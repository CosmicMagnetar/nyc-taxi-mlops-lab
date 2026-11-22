# 015: Chunk size, overlap and top-k

Stage: S6 · Date: 2026-11-22 · Author: Krishna · Drafted by agent: yes (wording drafted by the agent from the student's choice; the student owns it)

## Choice

Chunks of 256 tokens with 32 tokens of overlap, and the 3 closest chunks (top-k = 3) go into the prompt. Set in `pipelines/src/labpipes/defs/rag.py` (`CHUNK_TOKENS`, `OVERLAP_TOKENS`) and `app/src/rideapp/assistant.py` (`TOP_K`).

## Rejected alternative

Smaller chunks (128 tokens, overlap 16) with top-k = 4. They are sharper, but a policy sentence like a fee and its condition can end up split across two chunks, and then neither chunk answers the question alone.

## Why

The cost per request is mostly reading the prompt on the CPU LLM host: about 11 s per chunk. Top-k = 3 puts about 800 tokens of context in the prompt, around 33 s of reading before the answer starts. More chunks make each answer slower, so every extra chunk has to earn its place.

The wiki's pages are short, so 256 tokens usually holds a whole section. Chunks follow the headings and carry the page title and heading, so a chunk like "It is $4.50" is still findable. The overlap of 32 tokens keeps a sentence at a boundary in both neighbours without repeating much. An answer is only as good as the chunk that holds it, so I prefer chunks that keep a policy and its condition together.

This is a starting point chosen before seeing the wiki text. I will check it by asking a few wiki-only questions and seeing whether the right page is in `sources`.

## What would show this was wrong

- A wiki-only question whose answer is in the wiki but the right page is not among the 3 `sources`: k or the chunk size is too small.
- Answers cut off or wrong because the fact was split across two chunks: the chunks are too small or the overlap too short.
- Answers that take much longer than about 50 s: the context is too big.
