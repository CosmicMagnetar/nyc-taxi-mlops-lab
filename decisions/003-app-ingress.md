# 003: Open the demo app's HTTP port to the internet

Stage: S0 · Date: 2026-11-21 · Author: Krishna · Drafted by agent: yes

## Choice

Allow `0.0.0.0/0` to reach port 80 on the app host for the workshop demo. Keep the database, MLflow and LLM ports restricted to internal security groups.

## Rejected alternative

Allow only Krishna's current public IP address.

## Why

The laptop's address may change on campus Wi-Fi, and the instructor needs to reach the app for the S0 demo. The open port is limited to the HTTP app and will exist only while the lab resources are running.

## What would show this was wrong

Unexpected public traffic, abuse, or a requirement to limit the demo audience would justify switching to an allowlist or an authenticated front end.
