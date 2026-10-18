"""Checked, disposable S01 skill and native-loop startup overlay."""
from fusion.contracts import require

ORIGINAL = '''(= (metta $str)
   (let $code (sread $str)
        (repr (progn (call_with_inference_limit (Predicate (quote (eval $code $x))) 100000000) $x))))'''
ADAPTED = '''(= (metta $str)
   (if (py-call (neoclaw_bridge.recognizes $str))
       (py-call (neoclaw_bridge.invoke $str))
       (let $code (sread $str)
            (repr (progn (call_with_inference_limit (Predicate (quote (eval $code $x))) 100000000) $x)))))'''


def replace_once(source, before, after):
    require(source.count(before) == 1, 'UNSUPPORTED_PROFILE')
    return source.replace(before, after)


def adapted_skill(source):
    return replace_once(source, ORIGINAL, ADAPTED)


def adapted_loop(source):
    # Keep native getContext, parser, RESULTS/COMMAND_RETURN, history and state path.
    edits = [
        ('(initChannels)', '(initChannels) (change-state! &lastresults (py-call (loop_bridge.restore)))'),
        ('($respi (if', '($respi (if (py-call (loop_bridge.pending)) (py-call (loop_bridge.response)) (if'),
        ('(lib_llm_ext.useMiniMax $send)))))))', '(lib_llm_ext.useMiniMax $send))))))))'),
        ('($_ (println! (RESPONSE: $sexpr)))', '($_ (println! (RESPONSE: $sexpr))) ($indexed (py-call (loop_bridge.accept $respi $sexpr)))'),
        ('(let $s (superpose $sexpr)', '(let ($position $s) (superpose $indexed)'),
        ('(let $R (eval $s) (py-call (helper.normalize_string $R)))',
         '(let* (($_ (py-call (loop_bridge.begin $position $s))) ($R (eval $s)) ($_ (py-call (loop_bridge.end $position)))) (py-call (helper.normalize_string $R)))'),
        ('(change-state! &lastresults (string-safe (repr $results)))',
         '(progn (change-state! &lastresults (string-safe (repr $results))) (py-call (loop_bridge.finish (get-state &lastresults))))'),
        ('(mettaclaw (+ 1 $k))', '(if (py-call (loop_bridge.more)) (mettaclaw (+ 1 $k)) S01-BOUNDED-STOP)'),
    ]
    for before, after in edits:
        source = replace_once(source, before, after)
    return source
