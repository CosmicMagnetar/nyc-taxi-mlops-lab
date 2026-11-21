"""S1: the S3 sensor (and the job it starts).

Watch trips/ in the data bucket (DataBucket.trip_files). When a month's file appears or changes, add
the month to the trip_months partitions and request a run that goes from trip_files to zone_hour_stats.
The cursor maps each month to the ETag last requested, and the run key carries the ETag, so an unchanged
file never starts a second run and a replaced file starts exactly one.
"""

import json

import dagster as dg

from ..partitions import trip_months
from ..resources import DataBucket

# taxi_zones is included because zone_hour_stats joins it. The blocking checks on these assets run in
# the same job, so a month that fails one never reaches the mart.
ingest_month = dg.define_asset_job(
    "ingest_month",
    selection=dg.AssetSelection.assets("taxi_zones", "trip_files", "raw_trips", "stg_trips", "zone_hour_stats"),
)


@dg.sensor(job=ingest_month, minimum_interval_seconds=60)
def trip_file_sensor(context: dg.SensorEvaluationContext, data_bucket: DataBucket):
    seen: dict[str, str] = json.loads(context.cursor or "{}")
    files = data_bucket.trip_files()
    changed = [f for f in files if seen.get(f.month) != f.etag]
    if not changed:
        return dg.SkipReason("no new or changed trip files")
    new_months = [f.month for f in changed if f.month not in seen]
    return dg.SensorResult(
        run_requests=[dg.RunRequest(partition_key=f.month, run_key=f"{f.month}:{f.etag}") for f in changed],
        dynamic_partitions_requests=[trip_months.build_add_request(new_months)] if new_months else [],
        cursor=json.dumps({**seen, **{f.month: f.etag for f in changed}}, sort_keys=True),
    )
