# 018: Database role scope

Stage: S7 · Date: 2026-11-22 · Author: Krishna · Drafted by agent: yes (wording drafted by the agent from the student's choice; the student owns it)

## Choice

The MCP server runs as the Redshift user `lab_ro`, created by the `mcp_reader` asset (`pipelines/src/labpipes/defs/mcp_reader.py`, job `mcp_reader_job`) with no password (`password disable`, reached through the Data API's `--db-user` path). It has `USAGE` on schema `marts` and `SELECT` on `marts.zone_hour_stats`, nothing else: no access to `ingest` or `staging`, no write or create anywhere, no default privileges, a 30 s statement timeout and a connection limit of 5.

## Rejected alternative

`SELECT` on the whole `marts` schema, with default privileges so future mart tables are readable automatically. It is more convenient, but it is wider than the one tool needs, and a new table would become readable by the assistant without anyone deciding that it should be.

## Why

`query_zone_stats` needs one table. Least privilege means the database user can do only that, so even if the tool or the model misbehaves, or someone talks the assistant into a bad query, the worst case is reading aggregated zone statistics. It cannot read raw trips in `ingest` or `staging`, and it cannot change data.

The mart is rebuilt by `delete` and `insert` (the table is never dropped), and a grant belongs to the table, so the refresh does not remove the grant. The asset checks the result itself with `has_table_privilege` and `has_schema_privilege` and fails if the user can read the mart or write it wrongly, and `/healthz?db=1` on the MCP server shows the same facts, which the status workflow reports.

The tool also never formats input into SQL: there is one fixed query per metric, and the zone and hour are named parameters.

## What would show this was wrong

- The status artifact shows `write_marts`, `use_ingest` or `create_in_marts` as true for `lab_ro`.
- A new tool needs a second table: then I extend the grant for that table on purpose, not with a default privilege.
- Statements from the MCP user hit the 30 s timeout in normal use: the limit is too low for the mart's size.
