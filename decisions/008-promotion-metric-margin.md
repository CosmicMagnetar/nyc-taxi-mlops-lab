# 008: Promotion metric and margin

Stage: S2 · Date: 2026-11-21 · Author: CosmicMagnetar · Drafted by agent: yes

## Choice

A new version becomes `challenger` only if its holdout MAE is at least 10% lower than the champion's (or the v1 baseline's before a champion exists), and its p95 single-row predict latency is at most 10 ms. Both are enforced by the blocking `beats_champion` check.

## Rejected alternative

A 5% margin. It would let smaller real improvements through, at the cost of more challengers to review and a greater chance of promoting a difference that is only holdout noise.

## Why

<!-- Replace with your own reasoning before you submit. -->

In the notebook's 5% sample, v2 had an MAE of 3.7 minutes against 4.4 for v1, about 16% lower, so a 10% margin accepts a change of that size. p95 latency was 2.21 ms for v2 and 0.90 ms for v1, so 10 ms leaves about 4.5 times v2's measured latency for slower hosts.

The accepted risk: once a good champion exists, retrained versions will rarely be 10% better, so a real but small improvement may never reach serving.

## What would show this was wrong

<!-- Add what you would do about each signal. -->

Retrains stop producing challengers while slice errors or drift get worse, a challenger passes the gate but performs worse in the canary, or latency failures come from host noise and not from the model.
