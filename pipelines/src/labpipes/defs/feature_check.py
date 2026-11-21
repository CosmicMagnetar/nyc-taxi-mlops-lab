"""S2: the feature_contract check on trip_features.

contracts/features.yaml lists the model's inputs, label and the post-trip columns that must never be
inputs; contracts/mlflow.yaml says this check blocks. A month matches when the table has exactly the
contract's columns and types, no forbidden column, and no row outside a contract range.
"""

import dagster as dg

from ..contracts import features_contract
from ..partitions import check_month, trip_months
from ..resources import RedshiftData


def contract_columns(contract: dict) -> list[dict]:
    """The table's columns: keys, inputs and label. Derived inputs are not columns."""
    return [*contract["keys"], *contract["inputs"], contract["label"]]


def column_type(row: dict) -> str:
    """A catalog row's type, written the way features.yaml writes it."""
    if row["data_type"] == "character":
        return f"char({int(row['character_maximum_length'])})"
    return row["data_type"]


def column_problems(contract: dict, actual: dict[str, str]) -> list[str]:
    expected = {c["name"]: c["type"] for c in contract_columns(contract)}
    forbidden = {name.lower() for name in contract["forbidden"]}
    problems = [f"forbidden column: {name}" for name in sorted(actual) if name in forbidden]
    problems += [f"missing column: {name}" for name in expected if name not in actual]
    problems += [f"unexpected column: {name}" for name in sorted(actual) if name not in expected and name not in forbidden]
    problems += [
        f"{name}: expected type {want}, table has {actual[name]}"
        for name, want in expected.items()
        if name in actual and actual[name] != want
    ]
    return problems


def range_query(contract: dict, month: str) -> str:
    """Counts rows outside each contract range for one month. A null is out of range."""
    terms = []
    for column in contract_columns(contract):
        if "range" not in column:
            continue
        name, (low, high) = column["name"], column["range"]
        below = f"{name} <= {low}" if column.get("exclusive_min") else f"{name} < {low}"
        terms.append(f"sum(case when {name} is null or {below} or {name} > {high} then 1 else 0 end) as {name}")
    return f"select {', '.join(terms)} from staging.trip_features where trip_month = '{check_month(month)}'"


@dg.asset_check(
    asset="trip_features",
    partitions_def=trip_months,
    blocking=True,
    description="Columns, types and value ranges match contracts/features.yaml.",
)
def feature_contract(context: dg.AssetCheckExecutionContext, redshift: RedshiftData) -> dg.AssetCheckResult:
    contract = features_contract()
    rows = redshift.query(
        "select column_name, data_type, character_maximum_length from information_schema.columns "
        "where table_schema = 'staging' and table_name = 'trip_features'"
    )
    problems = column_problems(contract, {r["column_name"]: column_type(r) for r in rows})
    if not problems:  # the range query needs the contract's columns to exist
        counts = redshift.query(range_query(contract, context.partition_key))[0]
        problems = [f"{name}: {int(n)} row(s) out of range" for name, n in counts.items() if int(n or 0) > 0]
    return dg.AssetCheckResult(
        passed=not problems,
        severity=dg.AssetCheckSeverity.ERROR,
        description="; ".join(problems) if problems else "table matches the feature contract",
        metadata={"problems": dg.MetadataValue.json(problems)},
    )
