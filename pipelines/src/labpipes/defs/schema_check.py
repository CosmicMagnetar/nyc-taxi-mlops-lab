"""S1: the schema_contract check on trip_files.

Compare the landed file's Parquet footer (the DataBucket resource reads it) with
contracts/trips.schema.yaml, before raw_trips copies anything. contracts/platform.yaml says this check
is blocking. A mismatch is what the contract defines: a different column count, or a column at some
position with another name (ignoring case) or another storage type.
"""

import dagster as dg

from ..contracts import Column, trips_schema
from ..partitions import trip_months
from ..resources import DataBucket


def schema_mismatches(expected: list[Column], actual: list[Column]) -> list[str]:
    """Every difference between two ordered column lists. Parquet COPY maps columns by position."""
    problems = []
    if len(actual) != len(expected):
        problems.append(f"expected {len(expected)} columns, file has {len(actual)}")
    for position, (want, got) in enumerate(zip(expected, actual, strict=False), start=1):
        if got.name.lower() != want.name.lower():
            problems.append(f"column {position}: expected name {want.name}, file has {got.name}")
        if got.type != want.type:
            problems.append(f"column {position} ({want.name}): expected type {want.type}, file has {got.type}")
    for position, extra in enumerate(actual[len(expected) :], start=len(expected) + 1):
        problems.append(f"column {position}: unexpected {extra.name} ({extra.type})")
    for position, missing in enumerate(expected[len(actual) :], start=len(actual) + 1):
        problems.append(f"column {position}: missing {missing.name} ({missing.type})")
    return problems


@dg.asset_check(
    asset="trip_files",
    partitions_def=trip_months,
    blocking=True,
    description="The file's Parquet footer matches contracts/trips.schema.yaml.",
)
def schema_contract(context: dg.AssetCheckExecutionContext, data_bucket: DataBucket) -> dg.AssetCheckResult:
    footer = data_bucket.footer(context.partition_key)
    problems = schema_mismatches(trips_schema(), footer.columns)
    return dg.AssetCheckResult(
        passed=not problems,
        severity=dg.AssetCheckSeverity.ERROR,
        description="; ".join(problems) if problems else "footer matches the contract",
        metadata={
            "mismatches": dg.MetadataValue.int(len(problems)),
            "problems": dg.MetadataValue.json(problems),
        },
    )
