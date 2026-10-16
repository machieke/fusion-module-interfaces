"""The sole production composition point for this local integration harness."""
import json
from pathlib import Path
import sqlite3

from .adapters.detta import DettaStorage
from .service import Policy, Service
from .contracts import ContractError


def service(config_path, hook=lambda _: None):
    config = json.loads(Path(config_path).read_text())
    try:
        return Service(config["database"], DettaStorage(config["detta_binary"], config["da_root"]),
                       Policy(config_path), config.get("capacity", 8), hook)
    except sqlite3.Error as exc:
        raise ContractError("OVERLOADED" if "locked" in str(exc) else "NOT_AVAILABLE") from None
