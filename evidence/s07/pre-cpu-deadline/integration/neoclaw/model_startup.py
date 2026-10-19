"""Selected /9 source overlay. Native context, parser and execution stay native."""
import json
from pathlib import Path
from fusion.contracts import require
from .startup_overlay import replace_once

PROMPT = ('Generated shareable S07 test. Use only the two listed skills. '
          'Reply only with one command per line in the shown output format, without outer parentheses or argument quotes. '
          'For the first request call exactly the requested Truth_Deduction expression. '
          'After its actual COMMAND_RETURN appears, obey the second request by sending the approved reply. '
          'Do not calculate a substitute answer, add another command, explain, or use a code fence.')
SKILLS = ('- Send message to user: send string', '- Execute MeTTa expression: metta sexpression')
FORMAT = (' OUTPUT_FORMAT: Up to 5 lines, do not wrap quotes around args, do not use variables:_newline_'
          ' toolName1 arg1_newline_ toolName2 arg2_newline_ toolName3 arg3_newline_ toolName4 arg4_newline_ toolName5 arg5_newline_')


def scaffold():
    return 'PROMPT: '+PROMPT+' SKILLS: '+str(list(SKILLS)).replace("'",'_apostrophe_')+FORMAT


def extend(config,omega,directory,loop,skills,memory):
    source=loop.read_text()
    source=replace_once(source,'($send (py-str ($prompt :-:-:-: $lastmessage)))',
        '($send (py-call (loop_bridge.model_prompt (py-str ($prompt :-:-:-: $lastmessage)))))')
    start=source.index('($respi (if');end=source.index('($resp (py-call',start)
    source=replace_once(source,source[start:end],
        '($respi (if (py-call (loop_bridge.pending)) (py-call (loop_bridge.response)) (py-call (loop_bridge.model_complete $send))))\n                                       ')
    source=replace_once(source,'(loop_bridge.accept $respi $sexpr)','(loop_bridge.model_accept $respi $response $sexpr)')
    source=replace_once(source,'($sexpr (catch (sread $response)))',
        '($sexpr (catch (sread $response))) ($_ (py-call (loop_bridge.model_parsed $response (repr $sexpr))))')
    loop.write_text(source)
    original=(omega/'src/skills.metta').read_text()
    start=original.index('(= (getSkills)');end=original.index('\n\n',start)
    block=original[start:end]
    for description in SKILLS:require(json.dumps(description) in block,'UNSUPPORTED_PROFILE')
    skills.write_text(replace_once(skills.read_text(),block,'(= (getSkills) ('+' '.join(json.dumps(x) for x in SKILLS)+'))'))
    memory.write_text(replace_once(memory.read_text(),'(= (getPrompt) "Generated S03 memory read demonstration")',
        '(= (getPrompt) '+json.dumps(PROMPT)+')'))
    facade=directory/'s07_model.py'
    facade.write_text('''# The historical model fixture is not imported in this composition.
import sys
def forbidden(*args,**kwargs): raise RuntimeError('UNSELECTED_MODEL_FORBIDDEN')
useClaude=useOpenRouter=useMiniMax=useClaudeYoutubeImage=initLocalEmbedding=forbidden
sys.modules['lib_llm_ext']=sys.modules[__name__]
''')
    return facade
