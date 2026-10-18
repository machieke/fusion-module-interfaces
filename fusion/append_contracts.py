"""S03.2 bounded generated append composition; no mutable memory interface."""
from datetime import datetime
from . import vector_contracts as v, embedding_contracts as e, lookup_contracts as a
from .contracts import canonical, digest, require, decode
from .registry import Descriptor, Requirement, resolve, selection_token
from .responses import atom_write

APPLICATION = 'controlled-native-loop/5'
PROFILE = 'neoclaw-append-only-memory/1'
MEMORY_EMBEDDING = 'neoclaw-e5-memory-text/1'
BINDING = 'application/fusion-memory-append-binding-v1'
MAX_CALLS = 96
MAX_BUILDS = 3
MAX_WIRE_BYTES = 65536
ROLES = {'binding':BINDING, 'payload':v.PAYLOAD, 'vector':v.VECTOR, 'enrollment':v.ENROLLMENT}


def text(raw, helper, scope, corpus):
    e.text(raw);v.query_text(raw);e.text(helper)
    # Validate the intersection, including JSON escaping, before accepting a turn.
    v.payload(dict(scope=scope,corpus=corpus,uuid='00000000-0000-0000-0000-000000000000',
                   time='2000-01-01 00:00:00',content=raw),scope,corpus)
    return raw


def timestamp(value):
    require(type(value) is str and len(value)==19)
    try:require(datetime.strptime(value,'%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')==value)
    except ValueError:require(False)
    return value


def descriptors():
    return [Descriptor('s03.2-feed-detta' if name=='atom.storage' else 's03.2-chroma',name,version,'0.1.0',
            frozenset({a.FEED if name=='atom.storage' else v.PROFILE}),frozenset(operations),
            frozenset({'process-restart','scoped','idempotent'}),a.MAX_BYTES,privacy=v.PRIVACY,
            deterministic=name=='atom.storage',features=frozenset({PROFILE,v.EMBEDDING,v.EXTRACTION,v.INDEX}),
            receipt_providers=frozenset({'detta-local-rs/1'}))
            for name,version,operations in (
                ('atom.storage','1.2.0',('create','get','observe','head','readCommits')),
                ('search','3.1.0',('build','published')))]


def select(catalogue):
    return {d.interface:resolve(catalogue,Requirement(d.interface,d.version,
        '1.3.0' if d.interface=='atom.storage' else '3.2.0',next(iter(d.profiles)),d.operations,d.guarantees,
        privacy=v.PRIVACY,features=d.features)) for d in descriptors()}


def intent(value):
    v.fields(value,'profile session occurrence principal scope corpus uuid time content helper_input model vector_sha256 deadline_ms selections')
    require(value['profile']==PROFILE and value['model']==v.EMBEDDING,'UNSUPPORTED_PROFILE')
    for name in ('session','occurrence','uuid'):a.identity(value[name])
    for name in ('principal','scope','corpus'):require(type(value[name]) is str and 1<=len(value[name])<=80)
    timestamp(value['time']);text(value['content'],value['helper_input'],value['scope'],value['corpus'])
    require(type(value['vector_sha256']) is str and len(value['vector_sha256'])==64)
    a.integer(value['deadline_ms'],1,2**63-1)
    v.fields(value['selections'],'atom.storage search embedding')
    require(all(type(x) is str and len(x)==64 for x in value['selections'].values()))
    require(len(canonical(value))<=MAX_WIRE_BYTES)
    return a.copy(value)


def key(accepted,role):
    require(role in ROLES)
    return 'remember-'+accepted['occurrence']+'-'+role


def binding_bytes(accepted):
    # Opaque owner record binds the whole accepted append without duplicating text.
    return canonical(dict(profile=PROFILE,occurrence=accepted['occurrence'],intent_sha256=digest(canonical(intent(accepted)))))


def payload(accepted):
    return dict(scope=accepted['scope'],corpus=accepted['corpus'],uuid=accepted['uuid'],time=accepted['time'],content=accepted['content'])


def envelope(accepted, role, content_type, data):
    require(role in ROLES and content_type==ROLES[role],'UNSUPPORTED_PROFILE')
    require(type(data) is bytes and 1<=len(data)<=a.MAX_BYTES)
    if role=='binding':require(data==binding_bytes(accepted),'CONFLICT')
    elif role=='payload':require(data==canonical(payload(accepted)),'CONFLICT')
    elif role=='vector':
        v.from_bytes(data);require(digest(data)==accepted['vector_sha256'],'CONFLICT')
    else:
        import json
        entry=v.enrollment(json.loads(data),accepted['scope'],accepted['corpus'],accepted['model'])
        require(canonical(entry)==data and entry['uuid']==accepted['uuid'],'CONFLICT')
        require(entry['payload']['digest']==digest(canonical(payload(accepted))) and
                entry['vector']['digest']==accepted['vector_sha256'],'CONFLICT')
    return data


def request(value,chosen):
    v.fields(value,'request_id interface_ref operation scope profile selection intent body')
    accepted=intent(value['intent']);require(value['request_id']==accepted['occurrence'] and value['scope']==accepted['scope'],'CONFLICT')
    v.fields(value['interface_ref'],'id version');name=value['interface_ref']['id']
    require(name in chosen,'UNSUPPORTED_OPERATION');d=chosen[name]
    require(value['interface_ref']['version']==d.version,'UNSUPPORTED_VERSION')
    require(value['profile'] in d.profiles and value['selection']==selection_token(d)==accepted['selections'][name],'UNSUPPORTED_PROFILE')
    operation=value['operation'];body=value['body']
    require(operation in (('create','get','observe','authorize') if name=='atom.storage' else ('build','published')),'UNSUPPORTED_OPERATION')
    if operation=='create':
        v.fields(body,'role content_type data');envelope(accepted,body['role'],body['content_type'],decode(body['data']))
    elif operation=='observe':v.fields(body,'role');require(body['role'] in ROLES)
    elif operation=='get':v.fields(body,'ref');a.ref(body['ref'],value['scope'])
    elif operation=='authorize':v.fields(body,'mode');require(body['mode'] in ('write','disclose'))
    else:v.fields(body,'through');a.head(body['through'],value['scope'])
    require(len(canonical(value))<=MAX_WIRE_BYTES)
    return a.copy(value)


def observation(value,scope,descriptor,*,content_type=None,data=None):
    from .atom_observation import observation as accepted
    value=accepted(value,scope,descriptor)
    if value['found']:
        if content_type is not None:require(value['content_type']==content_type,'NOT_AVAILABLE')
        if data is not None:require(value['size']==len(data) and value['write']['ref']['digest']==digest(data),'NOT_AVAILABLE')
    return a.copy(value)
