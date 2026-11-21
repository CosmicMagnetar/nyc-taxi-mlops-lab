# 002: Tag each image with the full Git commit SHA

Stage: S0 · Date: 2026-11-21 · Author: Krishna · Drafted by agent: yes

## Choice

Publish the app image with the full commit SHA as its immutable tag. Deploy and roll back by choosing an exact SHA.

## Rejected alternative

Use a separately managed release/version tag.

## Why

The commit, image, deployment and `/version` response can all be matched directly without a release bookkeeping step during the two-day lab.

## What would show this was wrong

The team needs a release identifier spanning several repositories or a release approval process that Git commits alone cannot represent.
