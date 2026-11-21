#!/usr/bin/env bash
# Register a lab host through SSM. The one-time GitHub token is staged briefly in
# the private artifact bucket, never placed in an SSM command or its logs.
set +x
set -euo pipefail
export AWS_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 AWS_PAGER=""

role=${1:?usage: scripts/register-runner.sh [app|platform|llm]}
[[ "$role" =~ ^(app|platform|llm)$ ]] || { echo "unknown host role: $role" >&2; exit 2; }
root="$(cd "$(dirname "$0")/.." && pwd)"
repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
[[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || { echo "invalid GitHub repo" >&2; exit 1; }
policy=$(gh api "repos/$repo/actions/permissions/fork-pr-contributor-approval" -q .approval_policy)
[[ "$policy" == all_external_contributors ]] || {
  echo "Set Settings > Actions > General > Require approval for all external contributors before registering a runner." >&2
  exit 1
}
arn=$(aws sts get-caller-identity --query Arn --output text)
[[ "$arn" == *":assumed-role/voclabs/"* ]] || {
  echo "Refusing to use an account outside AWS Academy Learner Lab." >&2
  exit 1
}

instance_id=$(terraform -chdir="$root/infra/live" output -raw "${role}_instance_id")
bucket=$(terraform -chdir="$root/infra/live" output -raw artifact_bucket)
token=$(gh api -X POST "repos/$repo/actions/runners/registration-token" -q .token)
[[ -n "$token" ]] || { echo "GitHub did not issue a runner token." >&2; exit 1; }

prefix="runner-bootstrap/$role-$(date +%s)-$$"
tmp=$(mktemp -d)
chmod 700 "$tmp"
cleanup() {
  aws s3 rm "s3://$bucket/$prefix/token" --only-show-errors >/dev/null 2>&1 || true
  aws s3 rm "s3://$bucket/$prefix/runner-host.sh" --only-show-errors >/dev/null 2>&1 || true
  rm -f "$tmp/token"
  rmdir "$tmp" 2>/dev/null || true
}
trap cleanup EXIT
printf '%s' "$token" > "$tmp/token"
unset token
aws s3 cp "$tmp/token" "s3://$bucket/$prefix/token" --sse AES256 --only-show-errors
aws s3 cp "$root/scripts/runner-host.sh" "s3://$bucket/$prefix/runner-host.sh" --sse AES256 --only-show-errors

remote="set -e; f=\$(mktemp); trap 'rm -f \"\$f\"' EXIT; aws s3 cp 's3://$bucket/$prefix/runner-host.sh' \"\$f\" --only-show-errors; bash \"\$f\" '$repo' '$role' '$bucket' '$prefix/token'"
params=$(jq -cn --arg c "$remote" '{commands: [$c]}')
command_id=$(aws ssm send-command --instance-ids "$instance_id" --document-name AWS-RunShellScript \
  --parameters "$params" --comment "register lab-$role GitHub runner" \
  --query Command.CommandId --output text)

for _ in {1..120}; do
  status=$(aws ssm get-command-invocation --command-id "$command_id" --instance-id "$instance_id" \
    --query Status --output text 2>/dev/null || echo Pending)
  case "$status" in
    Success)
      echo "registered lab-$role on $instance_id"
      exit 0
      ;;
    Failed|Cancelled|TimedOut)
      aws ssm get-command-invocation --command-id "$command_id" --instance-id "$instance_id" \
        --query StandardErrorContent --output text >&2 || true
      echo "runner registration failed: $status" >&2
      exit 1
      ;;
  esac
  sleep 5
done
echo "runner registration timed out; inspect SSM command $command_id" >&2
exit 1
