# Runbook: serving-champion down (alert drill, S5)

Alert: `ModelFallbackFastBurn` (page). Meaning: more than 30% of quotes over 1h and 5m came from the static fallback, not the model.

## What a rider sees

Nothing breaks: `/predict` still answers 200, with `model.name = "static-median"` and `alias = null`. Availability and latency SLOs stay green; only the model-answers SLO sees it.

## Drill timeline (2026-11-22, UTC, about 1.7 requests/s of /predict)

| Time | Event |
|---|---|
| 11:14:47 | Break: `docker stop lab-serving-serving-champion-1` over SSM |
| 11:18:08 | Alert `pending` (+3m21s): 5m and 1h fallback ratios both over 0.3 |
| 11:20:09 | Alert `firing` (+5m22s), after the rule's `for: 2m` |
| 11:20:11 | Fix: `docker start lab-serving-serving-champion-1` |
| about 11:21 | `/predict` back to `trip-duration` v1, alias champion (first retry still fallback while the container became healthy, about 20 s) |

Detection took 5m22s. Where the time goes: scrape every 15 s, rule evaluation, the 5m window filling, and 2m `for`.

## Diagnose

1. `scripts/health.sh`, then check `lab_predictions_total{source="fallback"}` in Grafana.
2. On the app host (SSM): `docker ps | grep serving`, `docker logs --tail 50 lab-serving-serving-champion-1`.
3. Start it: `docker start lab-serving-serving-champion-1`; it is healthy in about 20 s. If the champion route still hangs afterwards, restart `lab-app-traefik-1` (known S3 hang).

## Not covered

If serving is down and traffic is under about 1 request in 10 s, the ratios are noisy; the alert may not fire. A lower `for:` or a minimum-traffic guard is a decision for the student.
