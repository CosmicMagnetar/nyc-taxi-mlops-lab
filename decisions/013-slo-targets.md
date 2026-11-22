# 013: SLO targets

Stage: S5 · Date: 2026-11-22 · Author: Krishna · Drafted by agent: yes (wording drafted by the agent from the student's reasoning; the student owns it)

## Choice

Three SLOs on `/predict`, each over 30 days:
- availability: 99.5% of requests are not 5xx
- latency: 95% of requests answer in 250ms or less
- model answers: 95% of quotes come from the model, not the static fallback

The details are in `observability/slo.yaml`, the rules and tests in `observability/rules/`.

## Rejected alternative

99.9% availability. It sounds better, but it leaves about 43 minutes of errors a month. One bad deploy, or the Traefik hang I saw in S3, would use all of it. The system is one app host with blue-green deploys, so I can't promise that.

## Why

How strict an SLO should be depends on how important the data is. If the app were more critical, I'd need a stricter target, but then downtime costs more and recovery has to be faster, which costs more effort and money. If it's too loose, riders suffer and I wouldn't notice. So I picked a value in between that fits this app: a taxi duration quote is useful but nobody is hurt if one is late or wrong for a few minutes.

- Availability 99.5%: about 3.6 hours of error budget a month. A 5xx means the rider gets nothing, so this is what they notice first.
- Latency p95 under 250ms: I used a percentile from the histogram, not an average, because an average hides the slow tail. 250ms is a bucket edge in `contracts/metrics.yaml`, so the number is exact and not estimated between buckets.
- Model answers 95%: when serving is down the app still answers 200 with the static median, so availability stays green while riders get a worse quote. I saw this in the drill. Without this third SLO that failure is invisible.

## What would show this was wrong

- The error budget is never touched for weeks: the targets are too loose and I could be stricter.
- Alerts page for things riders never noticed: the targets or the burn thresholds are too strict.
- An incident that riders felt but no SLO or alert saw: I'm missing an SLI.
- The fast-burn alert took 5m22s to fire in the drill. If that is too slow for a real outage, I'd shorten the windows or the `for:` time.
