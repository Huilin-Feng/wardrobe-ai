#!/usr/bin/env bash
# Deploys one immutable image tag on this host.
#
# Invoked as root by the wardrobe-ai-deploy SSM document, after the repository
# has been checked out at the same commit:
#   bash deploy/deploy.sh <40-character commit SHA>
#
# Steps: render .env from Parameter Store, log in to ECR, pull the images for
# this commit, restart the containers, and fail unless the API becomes healthy.
set -euo pipefail

IMAGE_TAG="${1:-}"
if [[ ! "$IMAGE_TAG" =~ ^[0-9a-f]{40}$ ]]; then
  echo "usage: deploy.sh <40-character commit SHA>" >&2
  exit 2
fi

APP_DIR="/opt/wardrobe-ai"
# SSM Run Command starts with a minimal PATH; snap-installed tools live in /snap/bin.
export PATH="$PATH:/snap/bin:/usr/local/bin"

set -a
# shellcheck source=/dev/null
. /etc/wardrobe-ai/bootstrap.env # AWS_REGION, SSM_PREFIX (written at first boot)
set +a

cd "$APP_DIR"

echo "==> Rendering .env from Parameter Store ($SSM_PREFIX)"
umask 077
tmp_env="$(mktemp)"
trap 'rm -f "$tmp_env"' EXIT

aws ssm get-parameters-by-path \
  --region "$AWS_REGION" \
  --path "$SSM_PREFIX" \
  --with-decryption \
  --query "Parameters[].[Name,Value]" \
  --output text |
  while IFS=$'\t' read -r name value; do
    printf '%s=%s\n' "${name##*/}" "$value"
  done >"$tmp_env"

for key in OPENAI_API_KEY WEATHER_API_KEY STORAGE_BACKEND S3_BUCKET ECR_REGISTRY LOG_GROUP; do
  if ! grep -q "^${key}=" "$tmp_env"; then
    echo "Missing parameter: $SSM_PREFIX/$key" >&2
    exit 1
  fi
done

{
  echo "IMAGE_TAG=$IMAGE_TAG"
  echo "WEB_PORT=80"
} >>"$tmp_env"

mv "$tmp_env" .env
chmod 600 .env

env_value() { grep -m1 "^$1=" .env | cut -d= -f2- || true; }
ECR_REGISTRY="$(env_value ECR_REGISTRY)"
DOMAIN_NAME="$(env_value DOMAIN_NAME)"

echo "==> Logging in to ECR"
aws ecr get-login-password --region "$AWS_REGION" |
  docker login --username AWS --password-stdin "$ECR_REGISTRY" >/dev/null

compose_files=(-f compose.yaml -f deploy/compose.prod.yaml)
if [[ -n "$DOMAIN_NAME" && -d "/etc/letsencrypt/live/$DOMAIN_NAME" ]]; then
  echo "==> Certificate found: serving HTTPS for $DOMAIN_NAME"
  compose_files+=(-f deploy/compose.https.yaml)
else
  echo "==> No certificate yet: serving HTTP only"
fi

echo "==> Pulling images for ${IMAGE_TAG:0:7}"
docker compose "${compose_files[@]}" pull

echo "==> Starting containers"
docker compose "${compose_files[@]}" up -d --no-build --remove-orphans

echo "==> Waiting for the API health check"
for attempt in $(seq 1 30); do
  if curl -fsS --max-time 3 http://127.0.0.1:8000/api/health >/dev/null; then
    echo "API healthy after $attempt attempt(s)"
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    echo "API did not become healthy. Recent logs:" >&2
    docker compose "${compose_files[@]}" logs --tail 50 api >&2 || true
    exit 1
  fi
  sleep 2
done

echo "==> Removing unused images older than a week"
docker image prune -af --filter "until=168h" >/dev/null || true

echo "==> Deployed ${IMAGE_TAG:0:7}"
