#!/usr/bin/env bash
# Runs on a lab EC2 host through SSM; receives only an S3 object key, never a token argument.
set +x
set -euo pipefail
export AWS_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 AWS_PAGER=""

repo=${1:?repo required}
role=${2:?role required}
bucket=${3:?bucket required}
token_key=${4:?token key required}
[[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || exit 2
[[ "$role" =~ ^(app|platform|llm)$ ]] || exit 2
command -v aws >/dev/null || { echo "AWS CLI is missing on the host" >&2; exit 1; }
[[ -f /var/lib/lab-setup-done ]] || { echo "host bootstrap is not complete" >&2; exit 1; }

cd /opt/actions-runner
if [[ -f .runner ]]; then
  ./svc.sh start
  echo "existing lab-$role runner service started"
  exit 0
fi

token=$(aws s3 cp "s3://$bucket/$token_key" - --only-show-errors)
[[ -n "$token" ]] || { echo "runner registration token is empty" >&2; exit 1; }
version=2.338.2
expected_sha256=670adb2f268fe21dcbb58b3db0e0aa9d5b3bddfe2c651481336e561ff86de945
archive=$(mktemp)
trap 'rm -f "$archive"' EXIT
curl -fsSL "https://github.com/actions/runner/releases/download/v$version/actions-runner-linux-arm64-$version.tar.gz" -o "$archive"
printf '%s  %s\n' "$expected_sha256" "$archive" | sha256sum -c - >/dev/null
tar -xzf "$archive" -C /opt/actions-runner
chown -R runner:runner /opt/actions-runner
sudo -u runner ./config.sh --unattended --replace \
  --url "https://github.com/$repo" --token "$token" \
  --name "lab-$role" --labels "lab-$role" --work _work
unset token
./svc.sh install runner
./svc.sh start
echo "lab-$role runner service installed and started"
