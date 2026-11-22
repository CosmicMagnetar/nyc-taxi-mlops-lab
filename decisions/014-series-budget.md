# 014: Series budget

Stage: S5 · Date: 2026-11-22 · Author: Krishna · Drafted by agent: yes

## Choice

Keep-list in `observability/alloy/budget.alloy`, aiming under about 4,000 active series for app and platform together, so the LLM host in S6 has room under Grafana Cloud's 10,000. Keep the contract's `lab_*` metrics, Traefik per-service request metrics (app and serving, not `@internal`), `up`, and a few node and container metrics (CPU, memory, root disk, real network devices). Drop everything else, and drop the labels `id`, `image` and `container_label_*` because they change on every deploy.

## Rejected alternative

A moderate budget (about 6,000): keep more container and node metrics. Less work to choose, but little room left for the LLM host in S6.

## Why

TODO (student, own words), with the measured number: run `count by (host, job) ({__name__=~".+"})` in Grafana Explore before and after, deploy three times (`gh workflow run cd.yaml`) and count again. Record the figures here. Measured 2026-11-22: 242 series before three extra deploys, 277 after (app 245, platform 24, rule outputs 8). Budget is 10,000.

## What would show this was wrong

TODO (student): e.g. active series above 4,000 after a burst of deploys (a label still changes per deploy), the LLM host in S6 not fitting, or an incident where a dropped metric was the one you needed.
