"""Trusted provider construction. Configuration selects modules, never wire callers."""
import json
from pathlib import Path
import sqlite3

from .adapters.detta import DettaStorage
from .adapters.fixture_atoms import FileAtomFixture
from .atoms import AtomOwner, AuthorizedAtoms
from .execution import ExecutionOwner, ExecutionSession
from .messaging import MessageOwner, MessagingSession
from .policy import Policy
from .ports import AtomStorage, CompletionDelivery, Messaging, DelegatedExecution
from .registry import descriptors, select
from .service import Service, SCHEMA
from .contracts import ContractError, require


def catalogue(config_path):
    config = json.loads(Path(config_path).read_text())
    return descriptors(atom_provider=config.get("atom_provider", "detta"))


def service(config_path, hook=lambda _: None):
    config = json.loads(Path(config_path).read_text())
    db = None
    try:
        advertised = catalogue(config_path)
        chosen = select(advertised)
        policy = Policy(config_path)
        atoms_db = config.get("atoms_database", config["database"] + ".atoms")
        messages_db = config.get("messages_database", config["database"] + ".messages")
        require(len({str(Path(p).resolve()) for p in (config["database"], atoms_db, messages_db)}) == 3,
                "UNSUPPORTED_PROFILE")
        if config.get("atom_provider", "detta") == "detta":
            provider = AtomOwner(atoms_db, DettaStorage(config["detta_binary"], config["da_root"]))
        else:
            provider = FileAtomFixture(config.get("atom_records", config["database"] + ".records"), config["da_root"])
        require(isinstance(provider, AtomStorage), "UNSUPPORTED_PROFILE")
        atoms_for = lambda principal: AuthorizedAtoms(provider, policy, principal, chosen["atom.storage"])
        db = sqlite3.connect(config["database"], timeout=.2)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        # Old M1 journals are historical artifacts, not an implicit migration input.
        require(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='atoms'").fetchone() is None,
                "UNSUPPORTED_PROFILE")
        db.executescript(SCHEMA)
        mailbox = MessageOwner(messages_db, policy, config.get("capacity", 8))
        worker = ExecutionOwner(db, policy, atoms_for("worker"), mailbox, config.get("capacity", 8))
        messaging_for = lambda principal, message_id: MessagingSession(mailbox, policy, principal, atoms_for(principal), message_id)
        execution_for = lambda principal, message_id: ExecutionSession(worker, principal, message_id)
        require(isinstance(mailbox, CompletionDelivery) and isinstance(messaging_for("worker", "probe"), Messaging)
                and isinstance(execution_for("worker", "probe"), DelegatedExecution), "UNSUPPORTED_PROFILE")
        return Service(db, policy, atoms_for, messaging_for, execution_for, worker, advertised, hook)
    except (sqlite3.Error, OSError) as exc:
        if db is not None:
            db.close()
        raise ContractError("OVERLOADED" if "locked" in str(exc) else "NOT_AVAILABLE") from None
    except BaseException:
        if db is not None:
            db.close()
        raise
