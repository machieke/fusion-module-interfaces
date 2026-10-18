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
    return bootstrap,memory
