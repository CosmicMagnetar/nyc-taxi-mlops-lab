#!/usr/bin/env bash
# Install scripts/boot-restore.sh on the platform host as a systemd unit that runs at every boot (S4).
#
#   scripts/install-boot-hook.sh
#
# Goes through SSM Run Command: no SSH. It's idempotent, so run it again after you change
# boot-restore.sh. It does not run the script: that happens at the next boot.
set -euo pipefail
export AWS_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 AWS_PAGER=""
root="$(cd "$(dirname "$0")/.." && pwd)"

iid=$(aws ec2 describe-instances \
  --filters Name=tag:project,Values=mlops-lab Name=tag:role,Values=platform Name=instance-state-name,Values=running \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)
[[ $iid == i-* ]] || { echo "no running platform host found" >&2; exit 1; }

script=$(base64 < "$root/scripts/boot-restore.sh" | tr -d '\n')
unit=$(base64 <<'EOF' | tr -d '\n'
[Unit]
Description=Bring RDS and Redshift back after a boot
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/lab-boot-restore.sh

[Install]
WantedBy=multi-user.target
EOF
)

cmds=$(jq -cn --arg s "$script" --arg u "$unit" '{commands: [
  "echo \($s) | base64 -d > /usr/local/bin/lab-boot-restore.sh && chmod 755 /usr/local/bin/lab-boot-restore.sh",
  "echo \($u) | base64 -d > /etc/systemd/system/lab-restore.service",
  "systemctl daemon-reload && systemctl enable lab-restore.service && systemctl is-enabled lab-restore.service"]}')
id=$(aws ssm send-command --instance-ids "$iid" --document-name AWS-RunShellScript --parameters "$cmds" \
  --comment "install lab-restore boot hook" --query Command.CommandId --output text)
status=InProgress
until [[ $status != InProgress && $status != Pending ]]; do
  sleep 2
  status=$(aws ssm get-command-invocation --command-id "$id" --instance-id "$iid" --query Status --output text 2>/dev/null || echo Pending)
done
aws ssm get-command-invocation --command-id "$id" --instance-id "$iid" --query '[Status,StandardOutputContent,StandardErrorContent]' --output text
[[ $status == Success ]]
