# S6 recall check: my answers

**1. What retrieval adds that fine-tuning doesn't, and its cost per request**
Retrieval gives the model fresh, private knowledge (the ops wiki) without retraining: when the wiki changes I re-embed only what changed, and the answer is up to date. Fine-tuning costs a lot upfront and the knowledge is frozen at training time. The cost of retrieval is paid on every request: an embedding call for the question, a vector search, and a longer prompt that the model must read. On the CPU LLM host that was about 11 seconds per chunk, and 40 seconds for a 3-chunk answer, against 5 seconds without the wiki. A fine-tuned model is cheaper per request because its prompt stays short.

**2. Cosine distance, and why the same model for question and document**
A small cosine distance means the two embedding vectors point in nearly the same direction, so the texts mean similar things. The question and the documents must be embedded by the same model because each model has its own vector space: vectors from two different models are not comparable. That is also why nomic uses two prefixes (`search_query:` and `search_document:`) and why I must re-embed everything if the model ever changes.

**3. HTTP ETag, `If-None-Match` and a 304**
An ETag is a fingerprint of a page's current version. I store the last one and send it in `If-None-Match`. If it still matches, the server answers 304 Not Modified, which carries no body, only headers, so I skip downloading and re-embedding the page. In my runs: first run 16 pages fetched and 16 chunks embedded; second run 0 fetched (16 unchanged) and 0 embedded.

**4. HNSW and IVFFlat**
HNSW is a graph index: better recall and fast queries, but more memory and a slower build. It can be created on an empty table and keeps working as chunks change, which suits a wiki re-read every day. IVFFlat clusters the vectors with k-means into lists and searches only the nearest ones: smaller and faster to build, but lower recall, it needs data in the table first, and it gets worse as the content changes until it is rebuilt. I chose HNSW (decision 016).
