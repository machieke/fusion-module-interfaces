"""Source-checked S06 receive/newness/send hooks; actual loop and parser retained."""
import json
import os
from pathlib import Path
import socket
import sys
from fusion.contracts import require
from .startup_overlay import replace_once


def extend(channels,loop,directory):
    source=channels.read_text()
    start=source.index('(= (initChannels)');end=source.index(';Receive the latest',start)
    source=replace_once(source,source[start:end],'''(= (initChannels)
   (progn (configure commchannel irc)
          (change-state! &lastsend (py-call (loop_bridge.channel_lastsend)))))

''')
    start=source.index('(= (send $msg)');end=source.index(';Search the internet',start)
    source=replace_once(source,source[start:end],'''(= (send $msg)
   (let $receipt (py-call (loop_bridge.channel_send $msg))
        (progn (change-state! &lastsend $msg) $receipt)))

''')
    source=replace_once(source,'irc.getLastMessage','s06_channel.getLastMessage')
    channels.write_text(source)
    text=loop.read_text()
    old='''($msgnew (prog1 (and (> (string_length $msgrcv) 0) (!= $msgrcv (get-state &prevmsg)))
                                             (if (> (string_length $msgrcv) 0) (change-state! &prevmsg $msgrcv) _)))'''
    text=replace_once(text,old,'''($msgnew (prog1 (py-call (loop_bridge.channel_new))
                                             (change-state! &prevmsg $msgrcv)))''')
    loop.write_text(text)
    # PeTTa appends Python import paths; a shared basename could resolve the
    # historical fixture directory first. Use a selected-profile module name.
    facade=directory/'s06_channel.py'
    facade.write_text('''from integration.neoclaw.channel_startup import install_guard
install_guard()
def getLastMessage():
 import loop_bridge
 return loop_bridge.input_message()
def start_irc(*args): raise RuntimeError('LEGACY_IRC_FORBIDDEN')
def send_message(*args): raise RuntimeError('LEGACY_IRC_FORBIDDEN')
''')
    return facade


def install_guard():
    app=json.loads(Path(os.environ['NEOCLAW_S01_APPLICATION']).read_text())
    cfg=json.loads(Path(app['channel_config']).read_text())
    allowed={cfg['endpoint']['port']} if cfg['placement']=='network' else set()
    if app['composition'] in ('controlled-native-loop/9','controlled-native-loop/10'):
        model=json.loads(Path(app['model_config']).read_text())
        allowed.add(model['endpoint']['port'] if model['placement']=='network' else model.get('backend_port',11434))
    def guard(event,args):
        if event=='socket.connect':
            sock,address=args
            if sock.family in (socket.AF_INET,socket.AF_INET6):
                if type(address) is not tuple or address[0]!='127.0.0.1' or address[1] not in allowed:
                    raise PermissionError('S06_NETWORK_ROUTE_REFUSED')
    sys.addaudithook(guard)
    require('irc' not in sys.modules,'UNSUPPORTED_PROFILE')
    # Probe in the actual native Python runtime. No channel handshake is allowed.
    blocked=False
    try:
        with socket.create_connection(('127.0.0.1',app['channel_irc_probe_port']),timeout=.2):pass
    except PermissionError:blocked=True
    require(blocked,'UNSUPPORTED_PROFILE')
    if app['composition'] in ('controlled-native-loop/9','controlled-native-loop/10'):
        refused=False
        probes={}
        if model['placement']=='network':
            try:
                with socket.create_connection(('127.0.0.1',model.get('backend_port',11434)),timeout=.2):pass
            except PermissionError:refused=True
            require(refused,'UNSUPPORTED_PROFILE')
            for path in app['model_denied_files']:
                try:
                    with open(path,'rb') as stream:stream.read(1)
                except OSError:probes[path]='inaccessible'
                else:require(False,'UNAUTHORIZED')
        require('integration.neoclaw.controlled.lib_llm_ext' not in sys.modules,'UNSUPPORTED_PROFILE')
        Path(app['workdir'],'model-boundary.json').write_text(json.dumps(dict(
            raw_ollama_connect_refused=refused,model_placement=model['placement'],
            selected_model_asset_probes=probes,
            loaded_facade=sys.modules['lib_llm_ext'].__file__,scripted_model_imported=False)))
    Path(app['workdir'],'channel-boundary.json').write_text(json.dumps(dict(
        direct_irc_connect_refused=blocked,mechanism='Python audit hook in source-checked native runtime; not an OS syscall sandbox',
        legacy_channel_buffer_imported=False,allowed_tcp_ports=sorted(allowed),
        denied_paths_visible=[p for p in app.get('denied_paths',[]) if Path(p).exists() and any(Path(p).iterdir())])))
