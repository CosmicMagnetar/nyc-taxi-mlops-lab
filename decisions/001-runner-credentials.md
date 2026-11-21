# 001: Use the EC2 instance profile for the runner

Stage: S0 · Date: 2026-11-21 · Author: Krishna · Drafted by agent: yes

## Choice

Use the app host's pre-created LabInstanceProfile for AWS access by its self-hosted runner.

## Rejected alternative

Put the Learner Lab's temporary session credentials in GitHub Actions secrets for the runner.

## Why

The profile supplies temporary credentials on the host and avoids copying session keys into GitHub. The runner will execute only trusted push/dispatch deployment jobs, never pull request code.

## What would show this was wrong

The runner cannot access the specific AWS APIs its jobs need through the profile, or its permissions are materially broader than the lab requires.
