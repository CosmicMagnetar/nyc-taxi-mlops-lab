# 016: HNSW or IVFFlat

Stage: S6 · Date: 2026-11-22 · Author: Krishna · Drafted by agent: yes (wording drafted by the agent from the student's choice; the student owns it)

## Choice

HNSW with cosine distance: `create index ... using hnsw (embedding vector_cosine_ops)` on `rag.chunks`, created with the table in `pipelines/src/labpipes/defs/rag.py`.

## Rejected alternative

IVFFlat. It is smaller and builds faster, but it clusters the vectors into lists when the index is built, so it needs data in the table first. As the wiki changes, new vectors fall into lists made for old content and recall drops until the index is rebuilt.

## Why

- HNSW can be created on an empty table and keeps working as chunks are added and removed. The wiki is re-read daily, so chunks come and go all the time, and I don't want a rebuild step to remember.
- It gives better recall for the same query speed. It costs more memory and a slower build, which does not matter for a wiki of a few hundred chunks.
- At a million chunks I would still pick HNSW if memory allows, because a rebuild of IVFFlat gets slow and recall depends on how the lists were trained. With this few chunks even an exact scan with no index would be fast; the index is for the habit and for growth.

## What would show this was wrong

- Recall falls as the wiki grows: for a known question, the right chunk is missing from the top-k although it exists.
- The index's memory or build time becomes a problem on the RDS instance.
- With only a few hundred chunks, an index may not be needed at all. If a plain scan is as fast, the index is just cost.
