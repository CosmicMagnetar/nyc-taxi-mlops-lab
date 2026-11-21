# 005: Which data-quality checks block, and their thresholds

Stage: S1 · Date: 2026-11-21 · Author: CosmicMagnetar · Drafted by agent: yes

## Choice

These checks on `stg_trips` block the month from reaching `zone_hour_stats`:

| Check | Blocks when | 2024-01..04 measured |
|---|---|---|
| Key fields null (pickup, dropoff, zones, fare) | any row | 0 rows |
| Duration <= 0 | over 0.1% | 0.027% to 0.031% |
| Negative fare | over 5% | 1.26% to 1.64% |
| Distance <= 0 | over 7.5% | 1.30% to 2.43% |
| Exact duplicate rows | over 0.01% | 0 to 1 row |
| Month row count | under 2,000,000 | 2,964,624 to 3,582,628 |

Null `passenger_count` only warns, above 15% (measured 4.7% to 11.9%). `schema_contract` also blocks, as `contracts/platform.yaml` requires.

## Rejected alternative

Blocking on `passenger_count` nulls above 15% or 20%. It would catch a collapse in that field, but the rate rose from 4.7% to 11.9% within four real months, so a fixed limit could stop a legitimate month.

## Why

<!-- Draft from the measured numbers. Replace with your own reasoning before you submit. -->

Key fields were never null, so any null is a clear fault. Range limits sit at roughly three times the worst real month, which leaves room for normal variation and still catches a corrupt month. A zero-duplicate rule would have blocked real 2024-02, which has one exact duplicate. The row-count floor catches a truncated file, which would otherwise pass the schema check.

The accepted risk: a month with very few passenger counts reaches the mart with only a warning, and a partial file above 2,000,000 rows passes.

## What would show this was wrong

<!-- Add what you would do about each signal. -->

A real month is stopped by a range or row-count check, a corrupt month reaches `zone_hour_stats` without being stopped, or the `passenger_count` warning fires on a month whose other fields look wrong.
