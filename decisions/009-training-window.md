# 009: Training window

Stage: S2 · Date: 2026-11-21 · Author: CosmicMagnetar · Drafted by agent: yes

## Choice

The holdout is the newest month with features, and training uses a 25% random sample of the three months before it. Today that means training on 2024-01..2024-03 and testing on 2024-04. The window rolls forward when a new month lands.

## Rejected alternative

Training on all earlier months. It would give more data for rare zone pairs, but memory and cost grow every month on an 8 GB host, and older patterns keep influencing the model.

## Why

<!-- Replace with your own reasoning before you submit. -->

Testing on the month after training matches how the model is used: it predicts trips later than anything it has seen. A random split of the same months would hide that. The three training months hold 9,452,562 valid trips, so a 25% sample is about 2.4 million rows, which fits alongside Dagster and MLflow. The distance lookup uses only the training window, so the holdout doesn't leak into it.

The accepted risks: seasons older than three months drop out, and random sampling means two runs don't train on identical rows.

## What would show this was wrong

<!-- Add the measurement you would act on. -->

Holdout MAE jumps when a new season arrives, rare-route slices get worse, or the training run comes close to the host's memory limit.
