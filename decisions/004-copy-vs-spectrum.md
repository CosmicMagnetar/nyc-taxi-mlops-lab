# 004: Load trip files with COPY

Stage: S1 · Date: 2026-11-21 · Author: CosmicMagnetar · Drafted by agent: yes

## Choice

Load each month into `ingest.raw_trips` with Redshift COPY. A rerun replaces that month's rows in one transaction.

## Rejected alternative

Redshift Spectrum: query the Parquet files in S3 without loading them. It avoids storing a second copy and has no reload to make idempotent, but every query scans S3 and the table gets no sort or distribution keys.

## Why

I chose COPY because it puts the data inside Redshift, which I think is better for analytics than querying files in S3 with Spectrum. The load covers 13,069,067 rows across 2024-01 to 2024-04.

The cost is storage in Redshift and a load step that must be safe to rerun. The temp-table load with delete and insert in one transaction covers the rerun.

## What would show this was wrong

Monthly COPY time or Redshift storage becomes the pipeline's main cost, or most raw months are rarely queried after staging is built.
