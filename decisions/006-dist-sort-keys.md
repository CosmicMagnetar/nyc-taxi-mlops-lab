# 006: Distribution and sort keys for the trip tables

Stage: S1 · Date: 2026-11-21 · Author: CosmicMagnetar · Drafted by agent: yes

## Choice

`ingest.raw_trips` uses `diststyle auto` and `sortkey (tpep_pickup_datetime)`. `staging.stg_trips` is given with `sortkey (pickup_at)` and no explicit distribution style.

## Rejected alternative

`sortkey (source_file)` on `raw_trips`. Every month reload and every `stg_trips` build filters on `source_file`, so this key would let those statements skip other months' blocks.

## Why

I chose pickup time over `source_file` because `source_file` is mainly used for deleting and reloading a month, while I expect pickup time to work better in the long run, with less change to the table's order as months are added. The trade-off I accept is that month deletes and `stg_trips` builds filter on `source_file`, so they get little direct pruning from this key.

The cluster is a single `ra3.large` node, so there is no network redistribution between nodes. `auto` leaves the choice to Redshift and needs no skew management. The cost is that the exact style can change over time.

## What would show this was wrong

Month reloads or `stg_trips` builds slow down noticeably as months accumulate, `svv_table_info` shows a high unsorted percentage on `raw_trips`, or the cluster grows to two nodes and zone joins start redistributing data.
