# 011: Blue-green switch is automatic after the smoke test

Stage: S3 · Date: 2026-11-22 · Author: Krishna · Drafted by agent: yes

## Choice

`app-deploy.yaml` switches traffic to the idle colour on its own once `deploy/web.sh smoke` passes: `/version` shows the deployed commit SHA and `/predict` answers. The previous colour keeps running.

## Rejected alternative

A reviewed click: the `production` reviewer approves the switch, like promotion and rollback. Safer for a bad deploy, but it slows every deploy and needs a person present.

## Why

Rollback is a reviewed click and took 2 seconds in the S3 run, with the old colour still running, so a bad deploy that passes smoke is cheap to undo. Promotion changes the model riders get, so it stays reviewed; a code deploy does not.

## What would show this was wrong

A deploy that passes smoke and then serves wrong answers or errors, such as an app silently falling back to the static median. That would call for stronger checks first: the idle colour answering with the champion, not the fallback.
