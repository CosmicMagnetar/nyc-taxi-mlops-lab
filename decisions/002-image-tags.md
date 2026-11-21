# 002: Tag each image with the full Git commit SHA

Stage: S0 · Date: 2026-11-21 · Author: Krishna · Drafted by agent: yes

## Choice

Publish the app image to GHCR as `ghcr.io/CosmicMagnetar/nyc-taxi-mlops-lab/app:<full-commit-sha>`.

The full 40-character Git commit SHA identifies the deployable image and is also placed in the app container as `GIT_SHA`. Rollback deploys a previously published SHA; it does not move or overwrite a mutable `latest` tag.

## Rejected alternative

Use a separately managed release/version tag or maintain only a mutable `latest` tag.

## Why

The commit, image, deployment and `/version` response can all be matched directly without an additional release bookkeeping step during the two-day lab.

An immutable tag is auditable and makes rollback explicit. It also allows the app host to run the blue-green deployment and compare the image tag with the running commit SHA.

## What would show this was wrong

The team needs a promotion identifier spanning several repositories or a formal release approval process that Git commits alone cannot represent. It would also be wrong if SHA tags make rollback or traceability harder than a simpler release sequence.
