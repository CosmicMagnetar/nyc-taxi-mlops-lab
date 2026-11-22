# Runbook: restore the lab after a session end

Owner: Krishna · Last run: 2026-11-22 · Time to restore last run: 4 min 45 s (triage to `health.sh` green, RDS was the slow part)

## When to use it

"The app quotes 12.25 minutes for every trip", "Dagster won't load", or Start Lab was just clicked and nothing answers. Run `scripts/health.sh` first: every FAIL and WARN it prints is a row below.

## Before you start

- Learner Lab: click **Start Lab**, wait for the green dot, then **AWS Details**, **Show**, and paste the credentials block into `~/.aws/credentials` (they expire with the session, and about two hours after a session end).
- `gh` logged in, and `infra/live` initialised (`terraform -chdir=infra/live init -backend-config=backend.hcl`).
- Session Manager plugin installed, for the Dagster and MLflow tunnels.

## Steps

Times are from the drill on 2026-11-22: RDS stopped, notebook stopped and Redshift paused at 06:53 UTC (the end-of-day shutdown), hosts left running. In a real overnight the hosts also come back with Start Lab.

| # | Check (command) | Healthy looks like | If not: fix (command) | Took | Automated? |
| --- | --- | --- | --- | --- | --- |
| 1 | `scripts/health.sh` line `session` | `OK session <arn>`; `aws sts get-caller-identity` works | New credentials from Learner Lab (Start Lab, AWS Details) | about 2 min, by hand | no: credentials stay with the person (nothing may store or type them) |
| 2 | `health.sh` line `rds` | `available` | `aws rds start-db-instance --db-instance-identifier lab`. A stop that is still finishing must complete first | stop took 6 min 25 s; start took 3 min 15 s (06:59:59 to 07:03:14) | yes: `scripts/restore.sh`; at host boot: `scripts/boot-restore.sh` |
| 3 | `health.sh` line `redshift` | `available` | `aws redshift resume-cluster --cluster-identifier lab` | 4 min 21 s (06:58:55 to 07:03:16) | yes: same two scripts |
| 4 | Dagster, MLflow, serving containers on the platform host | `docker ps` healthy, restart count 0 | Nothing to do: they never restarted, and kept running through the RDS outage. They answer again as soon as RDS is up (`restart: unless-stopped`, Docker enabled at boot) | 0 min after RDS was available | already automatic |
| 5 | `health.sh` line `status` | `OK ... status run N min ago` | `gh workflow run status.yaml` | under 1 min | yes: `scripts/restore.sh` dispatches it |
| 6 | `health.sh` line `laptop-ip` | `OK ... is in ingress_cidrs` | Add the laptop IP to `ingress_cidrs` in `infra/live/terraform.tfvars`, then `terraform apply` | not done in the drill | no: how wide to open ingress is a decision, and apply changes real infrastructure |
| 7 | `health.sh` line `notebook` | `Stopped` is fine (only exploration needs it) | `aws sagemaker start-notebook-instance --notebook-instance-name lab` when needed | about 6 min (brief's figure) | optional flag: `scripts/restore.sh --notebook` |
| 8 | `health.sh` line `predict` | `trip-duration champion <version>`, not the `static-median` fallback | Check serving (`deploy/web.sh status`). If the champion route hangs behind Traefik, `docker restart lab-app-traefik-1` on the app host (seen once, 2026-11-22) | 1 min | no: needs a person to judge |
| 9 | Dagster UI and MLflow UI tunnels | UIs load on localhost | `aws ssm start-session ... portNumber=3000,localPortNumber=3000`; MLflow `portNumber=5000,localPortNumber=5001` (macOS AirPlay owns local port 5000) | 1 min each | no: tunnels belong to the laptop |
| 10 | `health.sh` line `llm` | `OK ... runner not registered` is fine until S6 | none yet | n/a | n/a |

## Done when

- `scripts/health.sh` exits 0 (the laptop-ip WARN means exit 1 until step 6 is decided).
- `curl -X POST http://<app_public_ip>/predict ...` answers with `"alias": "champion"`.
- `gh workflow run status.yaml` is green and reports RDS and Redshift `available`.

## What we automated, and what we left as a step

See `decisions/012-restore-automation.md`.

- **Automated:** starting RDS, resuming Redshift and asking Dagster for a status run (`scripts/restore.sh`, from the laptop); starting RDS and resuming Redshift when the platform host boots (`scripts/boot-restore.sh`, installed by `scripts/install-boot-hook.sh`).
- **Left as steps:** credentials (nothing may handle them), `ingress_cidrs` and `terraform apply` (a decision with side effects), the notebook (costs money and is rarely needed), and the tunnels (they belong to the laptop).
