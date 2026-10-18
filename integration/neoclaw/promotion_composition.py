"""Fresh local S05 composition; provider choice changes only the selected owner."""
from pathlib import Path
import secrets
from fusion import promotion_contracts as c
from fusion.contracts import canonical
from fusion.promotion_composition import descriptor
from fusion.registry import descriptor_wire
from .evidence_composition import configure as evidence_configure


def configure(run,corpus,provider='sqlite',*,sources=None):
    value=evidence_configure(run,corpus,sources={} if sources is None else sources)
    root=run.h.caller_root/'private-attention';credential='private-'+secrets.token_hex(24);scope='private-s05'
    policy=dict(profile=c.PROFILE,placement='local',privacy='private-local-only',root=str(root),runtime=run.app['runtime'],
        scopes={scope:'A'},catalogue=[descriptor_wire(descriptor(provider))],clock_fixture=corpus['clock'],
        other_roots=[str(value['cognitive_root']),run.h.config['memory_read']['root']],
        principals={'A':dict(credential=credential,scopes={scope:['attention.'+o for o in c.OPERATIONS]})})
    path=run.h.caller_root/'attention-policy.json';path.write_bytes(canonical(policy));path.chmod(0o600)
    client=dict(policy=str(path),placement='local',credential=credential,scope=scope,context='synthetic-s05-global',
        output=str(run.h.caller_root/'private-context/promoted_memories.metta'))
    selected=run.h.caller_root/'attention-client.json';selected.write_bytes(canonical(client));selected.chmod(0o600)
    run.app.update(composition=c.APPLICATION,attention_config=str(selected));run.save()
    value.update(attention_root=root,attention_policy=path,attention_client=selected);return value
