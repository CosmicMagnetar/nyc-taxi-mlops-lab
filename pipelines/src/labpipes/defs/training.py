"""S2: training_set, trained_model, eval_report, the challenger gate and the challenger asset.

- training_set: UNLOAD a window of staging.trip_features (and the holdout month) to the artifact bucket.
  The zone-pair distance lookup (contracts/features.yaml, est_distance_miles) comes from the window only.
- trained_model: fit tripmodel.LightGBMModel (the given v2), log it to MLflow as a pyfunc with
  tripmodel.model_signature() and the tripmodel package bundled, register a version of the model named
  in contracts/mlflow.yaml, and tag it as that contract says.
- eval_report: tripmodel.evaluate the new version and the champion (or the v1 baseline before there is
  one) on the same holdout; log the metrics.
- beats_champion: a blocking check that guards the `challenger` asset, which sets the alias. The pipeline
  never moves `champion`.

The window, sample, margin and latency budget are the student's decisions (decisions 008 and 009).
"""

import os
from importlib.metadata import version as package_version
from pathlib import Path

import dagster as dg
import mlflow
import mlflow.pyfunc
from mlflow.exceptions import MlflowException

import tripmodel

from ..contracts import features_contract, mlflow_contract
from ..partitions import check_month
from ..resources import ArtifactBucket, MlflowTracking, RedshiftData

WINDOW_MONTHS = 3  # train on the three months before the newest one, which is the holdout
TRAIN_SAMPLE = 0.25  # share of the window's trips; the platform host has 8 GB
MIN_MAE_IMPROVEMENT = 0.10  # at least 10% lower holdout MAE than the champion or baseline
MAX_P95_LATENCY_MS = 10.0  # single-row predict, in process

MODEL_PACKAGES = ("lightgbm", "pandas", "numpy", "mlflow-skinny", "cloudpickle", "scikit-learn")


def choose_window(months: list[str]) -> tuple[list[str], str]:
    """The training months and the holdout month, from every month that has features."""
    ordered = sorted(check_month(m) for m in months)
    if len(ordered) < WINDOW_MONTHS + 1:
        raise ValueError(f"need {WINDOW_MONTHS + 1} months of features, found {len(ordered)}")
    return ordered[-(WINDOW_MONTHS + 1) : -1], ordered[-1]


def passes_gate(mae: float, reference_mae: float, p95_ms: float) -> list[str]:
    """Why a version may not become challenger. Empty when it passes."""
    problems = []
    limit = reference_mae * (1 - MIN_MAE_IMPROVEMENT)
    if mae > limit:
        problems.append(f"MAE {mae:.3f} is above {limit:.3f}, {MIN_MAE_IMPROVEMENT:.0%} below {reference_mae:.3f}")
    if p95_ms > MAX_P95_LATENCY_MS:
        problems.append(f"p95 latency {p95_ms:.2f} ms exceeds {MAX_P95_LATENCY_MS:.0f} ms")
    return problems


@dg.asset(deps=["trip_features"], group_name="model", kinds={"redshift", "s3"}, pool="redshift")
def training_set(
    context: dg.AssetExecutionContext, redshift: RedshiftData, artifacts: ArtifactBucket
) -> dg.Output[dict]:
    rows = redshift.query("select distinct trip_month from staging.trip_features")
    window, holdout = choose_window([r["trip_month"] for r in rows])
    in_window = ", ".join(f"''{m}''" for m in window)
    prefix = f"training/{context.run_id}"
    columns = "pickup_zone_id, dropoff_zone_id, pickup_hour, pickup_dow, duration_min"

    redshift.execute(
        f"unload ('select {columns} from staging.trip_features where trip_month in ({in_window}) "
        f"and random() < {TRAIN_SAMPLE}') to '{artifacts.uri(prefix + '/train/')}' iam_role default format parquet"
    )
    redshift.execute(
        f"unload ('select {columns} from staging.trip_features where trip_month = ''{holdout}''') "
        f"to '{artifacts.uri(prefix + '/holdout/')}' iam_role default format parquet"
    )
    redshift.execute(
        "unload ('select pickup_zone_id, dropoff_zone_id, median(trip_distance) as est_distance_miles "
        f"from staging.stg_trips where trip_month in ({in_window}) and duration_min > 0 and duration_min <= 180 "
        f"and trip_distance > 0 group by 1, 2') to '{artifacts.uri(prefix + '/distances/')}' "
        "iam_role default format parquet"
    )
    quoted = ", ".join(f"'{m}'" for m in window)
    counts = redshift.query(
        f"select sum(case when trip_month in ({quoted}) then 1 else 0 end) as train, "
        f"sum(case when trip_month = '{holdout}' then 1 else 0 end) as holdout from staging.trip_features"
    )[0]
    value = {"prefix": prefix, "window": window, "holdout": holdout}
    return dg.Output(
        value,
        metadata={
            "training_window": f"{window[0]}..{window[-1]}",
            "holdout_month": holdout,
            "train_sample": dg.MetadataValue.float(TRAIN_SAMPLE),
            "window_trips": dg.MetadataValue.int(int(counts["train"])),
            "holdout_trips": dg.MetadataValue.int(int(counts["holdout"])),
        },
    )


@dg.asset(group_name="model", kinds={"lightgbm", "mlflow"})
def trained_model(training_set: dict, artifacts: ArtifactBucket, tracking: MlflowTracking) -> dg.Output[dict]:
    client = tracking.client()
    contract = mlflow_contract()
    prefix = training_set["prefix"]
    train = artifacts.read_parquet(f"{prefix}/train")
    distances = artifacts.read_parquet(f"{prefix}/distances")
    model = tripmodel.LightGBMModel().fit(train, distances)
    window = f"{training_set['window'][0]}..{training_set['window'][-1]}"

    with mlflow.start_run(run_name=f"lightgbm {window}") as run:
        mlflow.log_params({"training_window": window, "holdout_month": training_set["holdout"],
                           "train_sample": TRAIN_SAMPLE, "train_rows": len(train), **model.params})
        info = mlflow.pyfunc.log_model(
            name="model",
            python_model=model,
            signature=tripmodel.model_signature(),
            code_paths=[str(Path(tripmodel.__file__).parent)],
            pip_requirements=[f"{name}=={package_version(name)}" for name in MODEL_PACKAGES],
        )
        registered = mlflow.register_model(info.model_uri, contract["registered_model"])

    tags = {
        "training_window": window,
        "holdout_month": training_set["holdout"],
        "features_version": str(features_contract()["version"]),
        "git_sha": os.environ.get("GIT_SHA", "unknown"),
    }
    for key, value in tags.items():
        client.set_model_version_tag(contract["registered_model"], registered.version, key, value)
    return dg.Output(
        {**training_set, "version": str(registered.version), "run_id": run.info.run_id},
        metadata={"version": str(registered.version), "train_rows": dg.MetadataValue.int(len(train))},
    )


@dg.asset(group_name="model", kinds={"mlflow"})
def eval_report(
    trained_model: dict, redshift: RedshiftData, artifacts: ArtifactBucket, tracking: MlflowTracking
) -> dg.Output[dict]:
    client = tracking.client()
    contract = mlflow_contract()
    name = contract["registered_model"]
    prefix = trained_model["prefix"]
    holdout = artifacts.read_parquet(f"{prefix}/holdout")
    boroughs = {
        int(r["location_id"]): r["borough"]
        for r in redshift.query("select location_id, borough from ingest.taxi_zones")
    }

    candidate = mlflow.pyfunc.load_model(f"models:/{name}/{trained_model['version']}")
    metrics = tripmodel.evaluate(candidate.predict, holdout, boroughs)

    try:
        champion = client.get_model_version_by_alias(name, "champion")
    except MlflowException:
        champion = None
    if champion is not None:
        reference = mlflow.pyfunc.load_model(f"models:/{name}@champion")
        reference_metrics = tripmodel.evaluate(reference.predict, holdout, boroughs)
        compared_with = f"champion v{champion.version}"
    else:
        baseline = tripmodel.BaselineModel().fit(
            artifacts.read_parquet(f"{prefix}/train"), artifacts.read_parquet(f"{prefix}/distances")
        )
        reference_metrics = tripmodel.evaluate(lambda df: baseline.predict(None, df), holdout, boroughs)
        compared_with = "v1 baseline"

    metrics["champion_mae_min"] = reference_metrics["mae_min"]
    for key in contract["metrics"]:
        if key in metrics:
            client.log_metric(trained_model["run_id"], key, metrics[key])
    for key in ("mae_min", "p95_latency_ms", "champion_mae_min"):
        client.set_model_version_tag(name, trained_model["version"], key, f"{metrics[key]:.4f}")

    report = {
        "version": trained_model["version"],
        "mae_min": metrics["mae_min"],
        "p95_latency_ms": metrics["p95_latency_ms"],
        "champion_mae_min": metrics["champion_mae_min"],
        "compared_with": compared_with,
    }
    return dg.Output(
        report,
        metadata={
            "version": report["version"],
            "compared_with": compared_with,
            "mae_min": dg.MetadataValue.float(report["mae_min"]),
            "champion_mae_min": dg.MetadataValue.float(report["champion_mae_min"]),
            "p95_latency_ms": dg.MetadataValue.float(report["p95_latency_ms"]),
        },
    )


@dg.asset_check(
    asset=eval_report,
    blocking=True,
    description="At least 10% lower holdout MAE than the champion or baseline, within the latency budget.",
)
def beats_champion(eval_report: dict) -> dg.AssetCheckResult:
    problems = passes_gate(eval_report["mae_min"], eval_report["champion_mae_min"], eval_report["p95_latency_ms"])
    return dg.AssetCheckResult(
        passed=not problems,
        severity=dg.AssetCheckSeverity.ERROR,
        description="; ".join(problems) if problems else f"beats {eval_report['compared_with']}",
        metadata={
            "mae_min": dg.MetadataValue.float(eval_report["mae_min"]),
            "champion_mae_min": dg.MetadataValue.float(eval_report["champion_mae_min"]),
            "p95_latency_ms": dg.MetadataValue.float(eval_report["p95_latency_ms"]),
        },
    )


@dg.asset(group_name="model", kinds={"mlflow"})
def challenger(eval_report: dict, tracking: MlflowTracking) -> dg.MaterializeResult:
    """Runs only when beats_champion passed in the same run. Never touches `champion`."""
    client = tracking.client()
    client.set_registered_model_alias(mlflow_contract()["registered_model"], "challenger", eval_report["version"])
    return dg.MaterializeResult(metadata={"version": eval_report["version"]})


train_model = dg.define_asset_job(
    "train_model", selection=dg.AssetSelection.assets(training_set, trained_model, eval_report, challenger)
)
