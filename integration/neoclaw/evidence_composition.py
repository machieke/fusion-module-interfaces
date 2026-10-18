"""Fresh local S04 operator recipe. Sources/model/channel are declared fixtures."""
import json
from pathlib import Path
import secrets
from fusion import nal_memory_contracts as c
from fusion.nal_private import descriptors,OPERATIONS
from fusion.registry import descriptor_wire,selection_token
from fusion.contracts import canonical,digest,require
from .append_composition import configure as append_configure
from .append_oracle import CREATED
from .evidence_oracle import SOURCE_LABEL

SCOPE='private-s04'
CONTEXT='generated-memory-assessment'
ASSUMPTION='generated-source-assessments-independent-with-compatibility-prior/1'
TEXT='Synthetic S04 source canary violet-paper-moons: observed a generated notebook.'
SECOND_LABEL='2031-04-05 06:09:10'


def policy(root,principal,credential,runtime,detta,*,origins=None):
    ds=descriptors();belief=next(x for x in ds if x.interface=='belief.revision')
    return dict(profile=c.PROFILE,placement='local',privacy='private-local-only',private_root=str(root),
        private_scopes={SCOPE:principal},private_descriptors=[descriptor_wire(x) for x in ds],
        principals={principal:dict(credential=credential,scopes={SCOPE:[n+'.'+o for n,ops in OPERATIONS.items() for o in ops]+['belief.revision.assume']})},
        origins={SCOPE:origins or {'controlled-source-a':'synthetic-channel-a','controlled-source-b':'synthetic-channel-b'}},
        assumptions=[ASSUMPTION],runtime=str(runtime),detta_binary=str(detta),shared_roots=[],
        evidence_consumer=dict(principal=principal,provider=belief.provider,profile=c.BELIEF_PROFILE,selection=selection_token(belief)))


def configure(run,corpus,*,sources=None,inputs=None):
    require(run.h.client['placement']=='local','UNSUPPORTED_PROFILE')
    value=append_configure(run,corpus,'local',inputs=inputs)
    cfg=policy(run.h.caller_root/'private-cognition','A','private-'+secrets.token_hex(24),run.app['runtime'],run.h.config['detta_binary'])
    cfg['shared_roots']=[run.h.config['memory_read']['root']]
    path=run.h.caller_root/'evidence-policy.json';path.write_bytes(canonical(cfg));path.chmod(0o600)
    client=dict(placement='local',scope=SCOPE,policy=str(path),credential=cfg['principals']['A']['credential'],context=CONTEXT,
        assumption=ASSUMPTION,sources=sources if sources is not None else {
            '2':dict(text=TEXT,label=SOURCE_LABEL,source='controlled-source-a'),
            '9':dict(text='Synthetic S04 second source: generated contrary notebook report.',label=SECOND_LABEL,source='controlled-source-b')})
    client_path=run.h.caller_root/'evidence-client.json';client_path.write_bytes(canonical(client));client_path.chmod(0o600)
    run.app.update(composition=c.APPLICATION,evidence_config=str(client_path));run.save()
    value.update(evidence_policy=path,evidence_client=client_path,cognitive_root=Path(cfg['private_root']))
    return value
