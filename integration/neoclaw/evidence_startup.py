"""Checked shared tvUpdate seam; original support/contradict wrappers retained."""
from .memory_oracle import query_source
from .startup_overlay import replace_once


def revision_wrappers(omega):
    query_source(omega)
    source=(omega/'src/memory.metta').read_text()
    pieces={name:source[source.index('(= ('+name+' '):source.index('\n(= (',source.index('(= ('+name+' ')+1)]
            for name in ('tvUpdate','support','contradict')}
    original='\n'.join(pieces.values())
    return replace_once(original,pieces['tvUpdate'],'''(= (tvUpdate $LTM_time $EPISODE_time $sign)
   (py-call (loop_bridge.revise $LTM_time $EPISODE_time (if $sign 1 0))))''')


def initialize_sources():
    # Declared channel fixture only; native receive/loop/parser remain upstream.
    import irc,loop_bridge
    irc.getLastMessage=loop_bridge.input_message
