# 003: Open the demo app's HTTP port to the internet

Stage: S0 · Date: 2026-11-21 · Author: Krishna · Drafted by agent: yes

## Choice

Set `ingress_cidrs = ["0.0.0.0/0"]` so any source may reach TCP port 80 on the app host for the workshop demo.

Keep RDS, MLflow, Dagster, the LLM hosts and all SSH access unreachable from public Internet traffic. Port 80 serves only the Traefik/app endpoint and the lab is expected to be torn down when the exercise ends.

## Rejected alternative

Restrict port 80 to a fixed `/32` allowlist containing only my current public IP.

## Why

The laptop's public address can change between networks and lab sessions. The S0 app is designed as a public smoke-test endpoint, and both the instructor and the grader may need to reach it without access to my AWS Session or laptop.

The exposure is intentionally narrow: only HTTP port 80 is public, and security groups keep stateful application dependencies private. The `/predict` endpoint is also non-credentialed and answers only the static demo quote.

## What would show this was wrong

Unexpected abuse, excessive unauthenticated traffic, sensitive data appearing in the API, or a requirement for a fixed demo audience should trigger a move to a fixed allowlist or an authenticated front end. I would also revisit this if the grader cannot reach the app through the public CIDR and needs explicit `/32` values added to `terraform.tfvars`.
