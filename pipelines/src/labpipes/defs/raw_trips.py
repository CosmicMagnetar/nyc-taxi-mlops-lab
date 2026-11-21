"""S1: the raw_trips asset.

One partition per month (partitions.trip_months), depending on trip_files. COPY the month's file into
Redshift with the LabRole attached to the cluster (`iam_role default`). Parquet COPY maps columns by
position, so it lands in a temp table with exactly the contract's columns; the month's old rows are then
replaced in the same transaction, so re-running a month never duplicates its rows and a failed load
leaves the previous rows in place. The landing columns come from contracts/trips.schema.yaml
(contracts.redshift_columns).
"""

import dagster as dg

from ..contracts import redshift_columns, trips_schema
from ..partitions import source_file, trip_months
from ..resources import DataBucket, RedshiftData


@dg.asset(partitions_def=trip_months, deps=["trip_files"], group_name="ingest", kinds={"redshift"}, pool="redshift")
def raw_trips(
    context: dg.AssetExecutionContext, redshift: RedshiftData, data_bucket: DataBucket
) -> dg.MaterializeResult:
    month = context.partition_key
    file = source_file(month)  # validates the partition key before it goes into SQL
    uri = data_bucket.trip_uri(month)
    columns = trips_schema()
    definitions = redshift_columns(columns)
    names = ", ".join(c.name.lower() for c in columns)

    redshift.execute(
        "create schema if not exists ingest",
        f"create table if not exists ingest.raw_trips ({definitions}, source_file varchar(64) not null) "
        "diststyle auto sortkey (tpep_pickup_datetime)",
        f"create temp table raw_trips_load ({definitions})",
        f"copy raw_trips_load from '{uri}' iam_role default format as parquet",
        f"delete from ingest.raw_trips where source_file = '{file}'",
        f"insert into ingest.raw_trips ({names}, source_file) select {names}, '{file}' from raw_trips_load",
    )
    rows = redshift.scalar(f"select count(*) from ingest.raw_trips where source_file = '{file}'")
    return dg.MaterializeResult(metadata={"rows": dg.MetadataValue.int(int(rows)), "source": uri})
