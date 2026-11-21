"""S1: data-quality checks on stg_trips (nulls, ranges, duplicates, row counts).

Thresholds are the student's decisions, set from 2024-01..04 as measured in Redshift. Bad rows stay in
stg_trips by design, so each check judges how much of a month is bad. Every check blocks the mart except
passenger_count nulls, which only warn: that rate rose from 4.7% to 11.9% across real months.
"""

import dagster as dg

from ..partitions import check_month, trip_months
from ..resources import RedshiftData

MIN_MONTH_ROWS = 2_000_000  # smallest real month: 2,964,624
MAX_PASSENGER_NULL_RATE = 0.15  # warn only; real months: 4.7% to 11.9%
MAX_DUPLICATE_RATE = 0.0001  # real months: 0 or 1 exact duplicate row
MAX_RANGE_RATES = {
    "nonpositive_duration": 0.001,  # real months: 0.027% to 0.031%
    "negative_fare": 0.05,  # real months: 1.26% to 1.64%
    "nonpositive_distance": 0.075,  # real months: 1.30% to 2.43%
}


def month_profile(redshift: RedshiftData, month: str) -> dict:
    """Row count and bad-row counts for one month."""
    m = check_month(month)
    return redshift.query(
        "select count(*) as rows, "
        "sum(case when pickup_at is null or dropoff_at is null or pickup_zone_id is null "
        "or dropoff_zone_id is null or fare_amount is null then 1 else 0 end) as null_keys, "
        "sum(case when passenger_count is null then 1 else 0 end) as null_passengers, "
        "sum(case when duration_min <= 0 then 1 else 0 end) as nonpositive_duration, "
        "sum(case when fare_amount < 0 then 1 else 0 end) as negative_fare, "
        "sum(case when trip_distance <= 0 then 1 else 0 end) as nonpositive_distance "
        f"from staging.stg_trips where trip_month = '{m}'"
    )[0]


def count(row: dict, key: str) -> int:
    """A count from a result row. SUM over no rows is NULL."""
    return int(row.get(key) or 0)


def rate(row: dict, key: str) -> float:
    rows = count(row, "rows")
    return count(row, key) / rows if rows else 0.0


def range_breaches(row: dict) -> list[str]:
    return [
        f"{key}: {rate(row, key):.3%} exceeds {limit:.3%}"
        for key, limit in MAX_RANGE_RATES.items()
        if rate(row, key) > limit
    ]


@dg.asset_check(
    asset="stg_trips", partitions_def=trip_months, blocking=True, description="Key fields are never null."
)
def key_fields_not_null(context: dg.AssetCheckExecutionContext, redshift: RedshiftData) -> dg.AssetCheckResult:
    bad = count(month_profile(redshift, context.partition_key), "null_keys")
    return dg.AssetCheckResult(
        passed=bad == 0,
        severity=dg.AssetCheckSeverity.ERROR,
        description=f"{bad} row(s) with a null pickup, dropoff, zone or fare",
        metadata={"bad_rows": dg.MetadataValue.int(bad)},
    )


@dg.asset_check(
    asset="stg_trips",
    partitions_def=trip_months,
    blocking=False,
    description="Warns when too many trips have no passenger_count.",
)
def passenger_count_nulls(context: dg.AssetCheckExecutionContext, redshift: RedshiftData) -> dg.AssetCheckResult:
    row = month_profile(redshift, context.partition_key)
    null_rate = rate(row, "null_passengers")
    return dg.AssetCheckResult(
        passed=null_rate <= MAX_PASSENGER_NULL_RATE,
        severity=dg.AssetCheckSeverity.WARN,
        description=f"{null_rate:.3%} null (limit {MAX_PASSENGER_NULL_RATE:.0%})",
        metadata={"null_rate": dg.MetadataValue.float(null_rate)},
    )


@dg.asset_check(
    asset="stg_trips",
    partitions_def=trip_months,
    blocking=True,
    description="Durations, fares and distances are in range for nearly all trips.",
)
def value_ranges(context: dg.AssetCheckExecutionContext, redshift: RedshiftData) -> dg.AssetCheckResult:
    row = month_profile(redshift, context.partition_key)
    breaches = range_breaches(row)
    return dg.AssetCheckResult(
        passed=not breaches,
        severity=dg.AssetCheckSeverity.ERROR,
        description="; ".join(breaches) if breaches else "all range rates within limits",
        metadata={key: dg.MetadataValue.float(rate(row, key)) for key in MAX_RANGE_RATES},
    )


@dg.asset_check(
    asset="stg_trips", partitions_def=trip_months, blocking=True, description="The month has few exact duplicates."
)
def duplicate_trips(context: dg.AssetCheckExecutionContext, redshift: RedshiftData) -> dg.AssetCheckResult:
    m = check_month(context.partition_key)
    row = redshift.query(
        "select sum(n) as rows, sum(n - 1) as extra from (select count(*) as n from staging.stg_trips "
        f"where trip_month = '{m}' group by vendor_id, pickup_at, dropoff_at, pickup_zone_id, dropoff_zone_id, "
        "trip_distance, total_amount)"
    )[0]
    duplicate_rate = rate(row, "extra")
    return dg.AssetCheckResult(
        passed=duplicate_rate <= MAX_DUPLICATE_RATE,
        severity=dg.AssetCheckSeverity.ERROR,
        description=f"{count(row, 'extra')} extra row(s), {duplicate_rate:.4%} (limit {MAX_DUPLICATE_RATE:.2%})",
        metadata={"extra_rows": dg.MetadataValue.int(count(row, "extra"))},
    )


@dg.asset_check(
    asset="stg_trips", partitions_def=trip_months, blocking=True, description="The month isn't truncated."
)
def month_row_count(context: dg.AssetCheckExecutionContext, redshift: RedshiftData) -> dg.AssetCheckResult:
    rows = count(month_profile(redshift, context.partition_key), "rows")
    return dg.AssetCheckResult(
        passed=rows >= MIN_MONTH_ROWS,
        severity=dg.AssetCheckSeverity.ERROR,
        description=f"{rows:,} rows (minimum {MIN_MONTH_ROWS:,})",
        metadata={"rows": dg.MetadataValue.int(rows)},
    )
