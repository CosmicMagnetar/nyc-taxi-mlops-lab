# 012: What the restore automates, and what stays a step

Stage: S4 · Date: 2026-11-22 · Author: Krishna · Drafted by agent: yes

## Choice

Two things are automated, and both only start things that are stopped:

- `scripts/restore.sh` from the laptop: start RDS, resume Redshift, wait until both are available, run the status workflow, print `health.sh`.
- `scripts/boot-restore.sh` on the platform host at every boot (a systemd unit): start RDS and resume Redshift when they are stopped or paused.

They never stop, pause, delete or change anything, never run `terraform apply`, never touch `ingress_cidrs` or the model aliases, and the notebook stays stopped unless asked for with `--notebook`. Credentials, the laptop IP and the tunnels stay as documented steps in `runbooks/restore.md`.

## Rejected alternative

Run `terraform apply` automatically after a restart so the laptop IP is added to `ingress_cidrs` too. It would remove one more manual step, but it is a change to real infrastructure and to who can reach the app, decided by a script nobody is watching.

## Why

In the drill the only things that did not come back by themselves were RDS and Redshift. Dagster, MLflow and serving never restarted and answered again once RDS was up, so they need no automation. RDS took 3 min 15 s to start and Redshift 4 min 21 s, the whole restore about 5 minutes, and those two start commands are safe to repeat. Credentials and ingress are different: one belongs to the person, the other widens who can reach the app, and a script should not decide either.

## What would show this was wrong

The boot hook starting RDS when I had stopped it on purpose (for example a reboot at end of day), or the script racing a stop that is still finishing. Also any restore that needed a step I had left as manual more than twice: that step then has earned its own automation.
