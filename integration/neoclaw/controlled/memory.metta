; Explicit unused-memory fixture facade. No Chroma, embedding or private store imports.
(= (maxFeedback) (empty))
(= (initMemory) (progn (configure maxFeedback 50000) (py-call (lib_llm_ext.memory_init))))
(= (getPrompt) "Generated S01.1 controlled demonstration")
(= (getHistory) "")
(= (best-promoted-memories) "")
(= (addToHistory $msg $response $sexpr $new) (py-call (lib_llm_ext.history_noop)))
