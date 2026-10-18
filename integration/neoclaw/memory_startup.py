"""Checked S03 startup extension; original local query composition is retained."""
import json
from pathlib import Path
from fusion.contracts import digest,require
from .memory_oracle import query_source,HELPER,HELPER_HASH
from .startup_overlay import replace_once

ROOT=Path(__file__).resolve().parents[2]


def extend(config,omega,petta,directory,loop):
    native=json.loads(Path(config['memory_native_config']).read_text())
    require(digest(Path(native.get('helper',HELPER)).read_bytes())==HELPER_HASH,'UNSUPPORTED_PROFILE')
    source=query_source(omega)
    source=replace_once(source,'lib_chromadb.query_with_ids_and_dists','loop_bridge.read_candidates')
    source=replace_once(source,'($current_time (get_time))','($current_time (py-call (loop_bridge.read_clock (py-call (memory_bootstrap.clock)))))')
    from fusion import append_contracts as w
    if config['composition']==w.APPLICATION:
        from .memory_oracle import creation_source
        creation=creation_source(omega)
        creation=replace_once(creation,'($current_time_str (get_time_as_string))',
            '($current_time_str (py-call (loop_bridge.remember_time (py-call (memory_bootstrap.creation_clock (get_time_as_string))))))')
        creation=replace_once(creation,'lib_chromadb.remember','loop_bridge.append_memory')
        creation=replace_once(creation,'lib_chromadb.link_episode','loop_bridge.creation_link')
        source+='\n'+creation
    memory=directory/'memory.metta'
    memory.write_text('''(= (maxFeedback) 50000)
(= (maxRecallItems) 2)
(= (maxSimilarityRecall) 4)
(= (promotionInflationFactor) 4)
(= (embeddingprovider) Local)
(= (initMemory) True)
(= (getPrompt) "Generated S03 memory read demonstration")
(= (getHistory) "")
(= (best-promoted-memories) "")
(= (addToHistory $a $b $c $d) True)
'''+source)
    text=loop.read_text()
    text=replace_once(text, '($R (eval $s))',
        '($R (if (py-call (loop_bridge.read_captured)) (py-call (loop_bridge.read_replay)) (eval $s))) '
        '($captured (py-call (loop_bridge.capture_native (py-call (helper.normalize_string $R)))))')
    text=replace_once(text,
        '($_ (py-call (loop_bridge.end $position)))) (py-call (helper.normalize_string $R)))',
        '($_ (py-call (loop_bridge.end $position)))) (py-call (helper.normalize_string $captured)))')
    loop.write_text(text)
    bootstrap=directory/'memory_bootstrap.py'
    bootstrap.write_text('from integration.neoclaw.memory_bootstrap import initialize, clock\ninitialize()\n')
    if config['composition']==w.APPLICATION:
        with bootstrap.open('a') as stream:stream.write('from integration.neoclaw.append_bootstrap import creation_clock\n')
    return bootstrap,memory
