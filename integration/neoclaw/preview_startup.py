"""Checked vocabulary overlay; preserves native balancing, sread and eval."""
from pathlib import Path
from fusion.contracts import digest, require
from fusion import neoclaw_contracts as c
from fusion.preview_application import configuration
from .startup_overlay import replace_once


def model_session(config, directory, loop):
    """Reuse native getContext/parser/evaluator; replace selected I/O only."""
    source = loop.read_text()
    source = replace_once(source, '($send (py-str ($prompt :-:-:-: $lastmessage)))',
        '($send (py-call (loop_bridge.model_prompt (py-str ($prompt :-:-:-: $lastmessage)))))')
    start = source.index('($respi (if'); end = source.index('($resp (py-call',start)
    source = replace_once(source, source[start:end],
        '($respi (if (py-call (loop_bridge.pending)) (py-call (loop_bridge.response)) (py-call (loop_bridge.model_complete $send))))\n                                       ')
    source = replace_once(source, '(loop_bridge.accept $respi $sexpr)', '(loop_bridge.model_accept $respi $response $sexpr)')
    source = replace_once(source, '($sexpr (catch (sread $response)))',
        '($sexpr (catch (sread $response))) ($_ (py-call (loop_bridge.model_parsed $response (repr $sexpr))))')
    # Equal text is a distinct input when the admitted occurrence is distinct.
    source = replace_once(source, '(and (> (string_length $msgrcv) 0) (!= $msgrcv (get-state &prevmsg)))',
                          '(> (string_length $msgrcv) 0)')
    loop.write_text(source)
    channels = directory/'preview_channels.metta'
    channels.write_text('''; Session inbox is real; IRC is not selected by this ingress profile.
(= (initChannels) True)
(= (receive) (py-call (loop_bridge.preview_input)))
(= (send $text) (Error send UNSELECTED_CHANNEL))
''')
    facade = directory/'preview_recorded_facade.py'
    facade.write_text('''# Model owner is called by loop_bridge, never by this facade.
import sys
def memory_init(): return True
def history_noop(): return True
def forbidden(*args, **kwargs): raise RuntimeError('UNSELECTED_MODEL_FORBIDDEN')
useClaude=useOpenRouter=useMiniMax=useClaudeYoutubeImage=initLocalEmbedding=forbidden
sys.modules['lib_llm_ext']=sys.modules[__name__]
''')
    return channels, facade


def extend(config, omega, directory, skills, loop):
    catalogue = configuration(config['preview'])
    source = (omega/'src/helper.py').read_text()
    require(digest(source.encode()) == c.PINS['sources']['mettaclaw']['files']['src/helper.py'], 'UNSUPPORTED_PROFILE')
    source = replace_once(source, '    "pin",', '    "pin",\n    "unpin",\n    "task-context",\n    "delegate",\n    "inspect-atom",')
    source = replace_once(source, 'special_two_arg_cmds = {', 'special_two_arg_cmds = {"pin", "delegate", ')
    source = replace_once(source, '"unlink", "support"', '"support"')
    helper = directory/'helper.py'
    helper.write_text(source)
    source = skills.read_text()
    start = source.index('(= (getSkills)')
    end = source.index('\n\n', start)
    source = replace_once(source, source[start:end], '(= (getSkills) (py-call (loop_bridge.preview_skills)))')
    source = replace_once(source, '(= (pin $x)\n   PIN-SUCCESS)',
        '(= (pin $item $note) (py-call (loop_bridge.preview_pin $item $note)))\n'
        '(= (unpin $item) (py-call (loop_bridge.preview_unpin $item)))\n'
        '(= (task-context) (py-call (loop_bridge.preview_inspect)))')
    # Keep trusted internal persistent-space export separate from model tools.
    # Renaming all original uses before adding wrappers prevents export! from
    # escaping the bounded-file adapter or trying to write an arbitrary path.
    for name in ('read','write','append'):
        source=source.replace('('+name+'-file ', '(preview-internal-'+name+'-file ')
    source += '\n(= (read-file $path) (py-call (loop_bridge.preview_read_file $path)))\n'
    source += '(= (write-file $path $text) (py-call (loop_bridge.preview_write_file $path $text)))\n'
    source += '(= (append-file $path $text) (py-call (loop_bridge.preview_append_file $path $text)))\n'
    source += '(= (episodes $selector) (py-call (loop_bridge.preview_episodes $selector)))\n'
    # Explicit supersession runs native remember preprocessing/creation, while
    # its accepted update identity selects the storage-owned successor CAS.
    source += '(= (forget $handle) (py-call (loop_bridge.preview_forget $handle)))\n'
    source += '(= (link $memory $history) (py-call (loop_bridge.preview_link $memory $history)))\n'
    source += '(= (unlink $relation) (py-call (loop_bridge.preview_unlink $relation)))\n'
    source += '(= (delegate $recipient $query) (py-call (loop_bridge.preview_delegate $recipient $query)))\n'
    source += '(= (inspect-atom $task) (py-call (loop_bridge.preview_inspect_atom $task)))\n'
    skills.write_text(source)
    # Actual native getContext evaluates the selected native sections; only
    # bounded deterministic allocation/rendering is an application policy.
    text=loop.read_text();start=text.index('(= (getContext)');end=text.index('\n(= (',start+1)
    loop.write_text(replace_once(text,text[start:end],'''(= (getContext)
        (string-safe (py-call (loop_bridge.preview_render_context
            (getPrompt) (getSkills) (get-state &lastresults) (getHistory)
            (best-promoted-memories) (get_time_as_string)))))
'''))
    return helper, catalogue.binding()
