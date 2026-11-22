# 013: SLO targets

Stage: S5 · Date: 2026-11-22 · Author: Krishna · Drafted by agent: yes

## Choice

Three SLOs over 30 days on `/predict`: availability 99.5% (non-5xx), latency 95% of requests under 250ms, and 95% of quotes from the model rather than the fallback. Details in `observability/slo.yaml`; rules and tests in `observability/rules/`. The 95% model-answers number is the agent's placeholder: confirm or change it.

## Rejected alternative

99.9% availability. Its budget is about 43 minutes a month, and one bad deploy or the Traefik champion-route hang from S3 would spend all of it on a single-host lab with blue-green deploys.

## Why

TODO (student, own words): why these three SLIs, why 99.5% and not stricter, why a p95 at 250ms (a bucket edge in `contracts/metrics.yaml`, so no interpolation) and why the model-answers SLO exists (the fallback keeps availability green while riders get a worse quote).

## What would show this was wrong

TODO (student): e.g. the budget is never touched in weeks (too loose), or alerts page for blips riders never noticed (too strict), or an incident that no SLO saw.
