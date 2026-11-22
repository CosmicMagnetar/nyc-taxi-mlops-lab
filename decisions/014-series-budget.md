# 014: Series budget

Stage: S5 · Date: 2026-11-22 · Author: Krishna · Drafted by agent: yes (wording drafted by the agent from the student's reasoning; the student owns it)

## Choice

A keep-list in `observability/alloy/budget.alloy`, aiming for under about 4,000 active series for the app and platform hosts together, so the LLM host in S6 has room under Grafana Cloud's 10,000. I keep:
- the contract's `lab_*` metrics, because every SLO and dashboard panel uses them
- Traefik's per-service request metrics for the app and serving services
- `up`
- a few node metrics (CPU, memory, root disk, real network devices)
- container memory and CPU

I drop everything else, and I drop the labels `id`, `image` and `container_label_*`.

## Rejected alternative

A moderate budget of about 6,000: keep more container and node metrics. It is less work to decide, but it leaves little room for the LLM host in S6, and I don't have a dashboard or alert that would use the extra metrics.

## Why

The rule I followed: keep what a dashboard, an SLO or an incident would use, and drop the rest. The labels `image` and `id` change on every deploy, so each deploy would make a whole new set of series. That is how the count creeps up over a day.

Measured on 2026-11-22: 242 series with no extra deploys, 277 after three more deploys (app 245, platform 24, rule outputs 8). The budget is 10,000, so this is under 3%. The deploys barely changed it, so the labels I dropped were the right ones.

## What would show this was wrong

- Active series go above about 4,000 after a burst of deploys: a label still changes per deploy.
- The LLM host in S6 doesn't fit in what is left.
- An incident where a metric I dropped was the one I needed.
- Being at 277 of 10,000 might also mean I was too strict. If I keep missing metrics, I should keep more.
