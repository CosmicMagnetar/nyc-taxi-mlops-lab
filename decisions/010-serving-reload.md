# 010: Serving reloads on alias change

Stage: S3 · Date: 2026-11-22 · Author: Krishna · Drafted by agent: yes

## Choice

Serving keeps running and picks up a new `champion` through `POST /reload`, which `promote.yaml` calls after it moves the alias. The old model keeps answering until the new one has loaded.

## Rejected alternative

Load only at start-up: restart or replace the serving container to change the model. Simpler, but a rider sees a gap or a container swap is needed for every promotion.

## Why

Riders should see no gap during a promotion. In the first promotion, serving went from no champion (503) to v1 with no container restart, and the app answered with the model after reload. A failed reload must leave the old model serving, which the given serving code does.

## What would show this was wrong

A reload that leaves serving without a working model, or serving memory growing across reloads. Also the Traefik hang seen after the first promotion: if it recurs on later promotions, reload is not safe behind Traefik's health checks and a start-up load with a container swap would be the fallback.
