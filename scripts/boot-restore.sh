#!/usr/bin/env bash
# Runs on the platform host at boot (S4), from the lab-restore systemd unit that
# scripts/install-boot-hook.sh installs. Dagster and MLflow need RDS and the marts need Redshift, and
# nothing else brings them back, so the host asks for them.
#
# Only ever starts RDS and resumes Redshift, and only when they are stopped or paused. It never stops,
# pauses, deletes or changes anything, and it does nothing at all while they are already running.
set -uo pipefail
export AWS_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 AWS_PAGER=""

log() { echo "boot-restore: $*"; }

# Right after boot the instance profile credentials can take a moment.
for _ in $(seq 1 12); do aws sts get-caller-identity >/dev/null 2>&1 && break; sleep 5; done

for _ in $(seq 1 40); do
  rds=$(aws rds describe-db-instances --db-instance-identifier lab --query 'DBInstances[0].DBInstanceStatus' --output text 2>/dev/null || echo unknown)
  case $rds in
    stopped) log "rds stopped, starting it"; aws rds start-db-instance --db-instance-identifier lab >/dev/null; break ;;
    stopping) sleep 15 ;;  # a stop is finishing: start has to wait for it
    *) log "rds is $rds, nothing to do"; break ;;
  esac
done

rs=$(aws redshift describe-clusters --cluster-identifier lab --query 'Clusters[0].ClusterStatus' --output text 2>/dev/null || echo unknown)
if [[ $rs == paused ]]; then
  log "redshift paused, resuming it"
  aws redshift resume-cluster --cluster-identifier lab >/dev/null
else
  log "redshift is $rs, nothing to do"
fi
