"""S6: the wiki RAG branch, in the `rag` database on RDS (pgvector), on a daily schedule.

    wiki_pages  ->  wiki_chunks  ->  wiki_embeddings  (+ blocking check: every chunk has a vector)

- wiki_pages: the published pages from the ops wiki (resource `wiki`: labpipes/wiki.py). Each page's ETag
  is stored and sent next time: an unchanged page costs a 304 and no body. Pages the wiki no longer lists
  are removed, with their chunks.
- wiki_chunks: changed pages are split with labpipes.chunking.chunk_markdown (CHUNK_TOKENS and
  OVERLAP_TOKENS: decision 015). A chunk's id is its content hash, so unchanged text keeps its id and its
  vector; chunks whose text is gone are deleted.
- wiki_embeddings: only chunks that have no vector yet are embedded (resource `embed`: nomic-embed-text,
  768 dimensions) and stored as pgvector `vector(768)`. The index is HNSW (decision 016).
The RDS admin connection comes from the `rag` resource (RagStore.connect).

Run by hand: scripts/dagster-run.sh ingest_wiki --wait. Run it twice: the second run's metadata shows
pages_fetched=0 and chunks_embedded=0.
"""

import dagster as dg

from ..chunking import chunk_markdown
from ..resources import LlmEmbed, RagStore, WikiApi

CHUNK_TOKENS = 256  # decision 015
OVERLAP_TOKENS = 32  # decision 015
DIMENSIONS = 768

SCHEMA = f"""
create extension if not exists vector;
create schema if not exists rag;
create table if not exists rag.pages (
    id text primary key,
    title text not null,
    updated_at text not null,
    etag text not null,
    body text not null,
    chunked_etag text
);
create table if not exists rag.chunks (
    id text primary key,
    page_id text not null references rag.pages(id) on delete cascade,
    idx integer not null,
    heading text not null,
    content text not null,
    tokens integer not null,
    embedding vector({DIMENSIONS})
);
create index if not exists chunks_page_idx on rag.chunks (page_id);
-- decision 016: HNSW builds on an empty table and stays good as the wiki changes
create index if not exists chunks_embedding_hnsw on rag.chunks using hnsw (embedding vector_cosine_ops);
"""


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
    conn.commit()


def vector_literal(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.7g}" for x in v) + "]"


@dg.asset(group_name="rag", kinds={"postgres"})
def wiki_pages(context: dg.AssetExecutionContext, wiki: WikiApi, rag: RagStore) -> dg.MaterializeResult:
    client = wiki.client()
    refs = client.pages()
    conn = rag.connect()
    fetched = unchanged = 0
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("select id, etag from rag.pages")
            stored = dict(cur.fetchall())
            for ref in refs:
                if stored.get(ref.id) == ref.etag:
                    unchanged += 1  # the listing already says it is unchanged: no request for the body
                    continue
                page = client.page(ref.id, stored.get(ref.id))  # a 304 here also means unchanged
                if page is None:
                    unchanged += 1
                    continue
                fetched += 1
                cur.execute(
                    """insert into rag.pages (id, title, updated_at, etag, body) values (%s, %s, %s, %s, %s)
                       on conflict (id) do update set title = excluded.title, updated_at = excluded.updated_at,
                                                      etag = excluded.etag, body = excluded.body""",
                    (page.id, page.title, page.updated_at, page.etag, page.body),
                )
            gone = sorted(set(stored) - {r.id for r in refs})
            if gone:
                cur.execute("delete from rag.pages where id = any(%s)", (gone,))  # chunks go with it
        conn.commit()
    finally:
        conn.close()
    context.log.info("wiki: %d listed, %d fetched, %d unchanged, %d removed", len(refs), fetched, unchanged, len(gone))
    return dg.MaterializeResult(metadata={
        "pages_listed": dg.MetadataValue.int(len(refs)),
        "pages_fetched": dg.MetadataValue.int(fetched),
        "pages_unchanged": dg.MetadataValue.int(unchanged),
        "pages_removed": dg.MetadataValue.int(len(gone)),
    })


@dg.asset(deps=[wiki_pages], group_name="rag", kinds={"postgres"})
def wiki_chunks(context: dg.AssetExecutionContext, rag: RagStore) -> dg.MaterializeResult:
    conn = rag.connect()
    added = removed = pages = 0
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("select id, title, body, etag from rag.pages where chunked_etag is distinct from etag")
            for page_id, title, body, etag in cur.fetchall():
                pages += 1
                chunks = chunk_markdown(title, body, CHUNK_TOKENS, OVERLAP_TOKENS)
                keep = []
                for c in chunks:
                    cid = c.content_hash(page_id)
                    keep.append(cid)
                    cur.execute(
                        """insert into rag.chunks (id, page_id, idx, heading, content, tokens) values (%s, %s, %s, %s, %s, %s)
                           on conflict (id) do update set idx = excluded.idx""",
                        (cid, page_id, c.index, c.heading, c.text, c.tokens),
                    )
                    added += cur.rowcount
                cur.execute("delete from rag.chunks where page_id = %s and not (id = any(%s))", (page_id, keep))
                removed += cur.rowcount
                cur.execute("update rag.pages set chunked_etag = %s where id = %s", (etag, page_id))
            cur.execute("select count(*) from rag.chunks")
            total = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    return dg.MaterializeResult(metadata={
        "pages_rechunked": dg.MetadataValue.int(pages),
        "chunks_written": dg.MetadataValue.int(added),
        "chunks_removed": dg.MetadataValue.int(removed),
        "chunks_total": dg.MetadataValue.int(total),
    })


@dg.asset(deps=[wiki_chunks], group_name="rag", kinds={"postgres"})
def wiki_embeddings(context: dg.AssetExecutionContext, embed: LlmEmbed, rag: RagStore) -> dg.MaterializeResult:
    conn = rag.connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("select id, content from rag.chunks where embedding is null order by id")
            todo = cur.fetchall()
        embedded = 0
        for i in range(0, len(todo), 32):  # commit as we go, so an interrupted run keeps its progress
            batch = todo[i : i + 32]
            vectors = embed.embed_documents([content for _, content in batch])
            with conn.cursor() as cur:
                for (cid, _), v in zip(batch, vectors, strict=True):
                    cur.execute("update rag.chunks set embedding = %s::vector where id = %s", (vector_literal(v), cid))
            conn.commit()
            embedded += len(batch)
            context.log.info("embedded %d/%d", embedded, len(todo))
        with conn.cursor() as cur:
            cur.execute("select count(*) from rag.chunks")
            total = cur.fetchone()[0]
    finally:
        conn.close()
    return dg.MaterializeResult(metadata={
        "chunks_embedded": dg.MetadataValue.int(embedded),
        "chunks_total": dg.MetadataValue.int(total),
    })


@dg.asset_check(asset=wiki_embeddings, blocking=True, description="Every chunk has a vector.")
def every_chunk_has_a_vector(context: dg.AssetCheckExecutionContext, rag: RagStore) -> dg.AssetCheckResult:
    conn = rag.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("select count(*) filter (where embedding is null), count(*) from rag.chunks")
            missing, total = cur.fetchone()
    finally:
        conn.close()
    return dg.AssetCheckResult(
        passed=missing == 0 and total > 0,
        severity=dg.AssetCheckSeverity.ERROR,
        description=f"{missing} of {total} chunk(s) have no vector" if total else "there are no chunks at all",
        metadata={"chunks_without_vector": dg.MetadataValue.int(int(missing)), "chunks_total": dg.MetadataValue.int(int(total))},
    )


ingest_wiki = dg.define_asset_job(
    "ingest_wiki",
    selection=dg.AssetSelection.assets(wiki_pages, wiki_chunks, wiki_embeddings) | dg.AssetSelection.checks(every_chunk_has_a_vector),
)

# The wiki is re-read daily; the ETags make an unchanged wiki a cheap run.
daily_wiki = dg.ScheduleDefinition(job=ingest_wiki, cron_schedule="0 6 * * *", execution_timezone="UTC")
