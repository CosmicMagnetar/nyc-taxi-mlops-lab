# 001: Use the EC2 instance profile for the runner

Stage: S0 · Date: 2026-11-21 · Author: Krishna · Drafted by agent: yes

## Choice

Use the app host's pre-created `LabInstanceProfile` for AWS access by the self-hosted GitHub Actions runner labeled `lab-app`.

The runner will not receive AWS access-key secrets or session credentials. Deployment commands on the host run as the runner user and obtain temporary credentials through the EC2 instance metadata service from `LabInstanceProfile`.

## Rejected alternative

Store `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN` in GitHub Actions secrets for the runner.

## Why

The profile supplies temporary, automatically rotated credentials and avoids copying Learner Lab session credentials into GitHub. This matches the lab rule that CI only builds and pushes images while CD executes on the app host.

The runner will execute trusted `main` deployments, not untrusted pull-request code. Static session credentials are tied to a single AWS Academy session and would expire before later lab stages; they would also have to be replaced manually after restarting the lab.

## What would show this was wrong

The runner cannot access the AWS APIs required for later lab stages through `LabInstanceProfile`, or the profile permissions are materially broader than the jobs require. It would also be wrong if GitHub-hosted runners become responsible for AWS operations that cannot use the host instance profile.
