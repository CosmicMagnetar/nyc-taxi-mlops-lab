#!/usr/bin/env bash
# Bring the lab back after a session end (S4). Run it from your laptop with this session's AWS credentials.
#
#   scripts/restore.sh [--notebook]
#
# Does, in order, and skips whatever is already fine: start RDS, resume Redshift, wait until both are
# available, ask Dagster for a fresh status run, then print scripts/health.sh.
# Never does: terraform apply or destroy, stopping or pausing anything, touching the model aliases,
# or editing ingress_cidrs (your laptop IP is a decision, so health.sh just warns about it).
# The notebook stays stopped unless you pass --notebook: only exploration needs it.
set -euo pipefail
export AWS_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 AWS_PAGER=""
root="$(cd "$(dirname "$0")/.." && pwd)"
notebook=''
[[ "${1:-}" == --notebook ]] && notebook=1

started=$(date +%s)
say() { printf '%s  %s\n' "$(date -u +%T)" "$*"; }

aws sts get-caller-identity >/dev/null || { echo "AWS credentials don't work: export this session's" >&2; exit 1; }

rds_status() { aws rds describe-db-instances --db-instance-identifier lab --query 'DBInstances[0].DBInstanceStatus' --output text; }
rs_status() { aws redshift describe-clusters --cluster-identifier lab --query 'Clusters[0].ClusterStatus' --output text; }

# RDS can only be started once it has finished stopping.
while [[ "$(rds_status)" == stopping ]]; do say "rds is still stopping, waiting"; sleep 15; done
if [[ "$(rds_status)" == stopped ]]; then
  say "starting rds"
  aws rds start-db-instance --db-instance-identifier lab --query 'DBInstance.DBInstanceStatus' --output text
fi
if [[ "$(rs_status)" == paused ]]; then
  say "resuming redshift"
  aws redshift resume-cluster --cluster-identifier lab --query 'Cluster.ClusterStatus' --output text
fi
if [[ -n "$notebook" ]]; then
  say "starting the notebook"
  aws sagemaker start-notebook-instance --notebook-instance-name lab 2>/dev/null || true
fi

until [[ "$(rds_status)" == available ]]; do say "rds: $(rds_status)"; sleep 15; done
say "rds available"
until [[ "$(rs_status)" == available ]]; do say "redshift: $(rs_status)"; sleep 15; done
say "redshift available"

# Dagster, MLflow and serving come back by themselves once RDS is up (restart: unless-stopped); the
# status run is what proves it, and the platform host reports RDS and Redshift in its artifact.
repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
gh workflow run status.yaml --repo "$repo" >/dev/null && say "status workflow started"

say "restore took $(( $(date +%s) - started ))s; state now:"
"$root/scripts/health.sh" || true
