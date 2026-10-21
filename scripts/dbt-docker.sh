#!/usr/bin/env bash
# Run dbt inside the pinned Docker image against Snowflake, using the SNOWFLAKE_* values in .env.
#
#   scripts/dbt-docker.sh build --target dev
#   scripts/dbt-docker.sh source freshness --target dev
#   scripts/dbt-docker.sh --version
#
# Only SNOWFLAKE_* variables are passed to the container (never ServiceNow credentials), and the
# private key is mounted read-only. Set DBT_IMAGE to use a different image name.
set -euo pipefail

cd "$(dirname "$0")/.."
image="${DBT_IMAGE:-dq-gate-dbt}"

if [[ ! -f .env ]]; then
  echo "Missing .env (copy .env.example and fill in the SNOWFLAKE_* values)." >&2
  exit 1
fi

key_path="$(grep -E '^SNOWFLAKE_PRIVATE_KEY_PATH=' .env | head -n1 | cut -d= -f2-)"
key_path="${key_path/#\~/$HOME}"
if [[ -z "$key_path" || ! -f "$key_path" ]]; then
  echo "SNOWFLAKE_PRIVATE_KEY_PATH in .env does not point to an existing file." >&2
  exit 1
fi

docker build -q -t "$image" -f dbt/Dockerfile . >/dev/null

exec docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env-file <(grep -E '^SNOWFLAKE_' .env) \
  -e SNOWFLAKE_PRIVATE_KEY_PATH="/keys/$(basename "$key_path")" \
  -e HOME=/tmp \
  -v "$PWD":/workspace \
  -v "$(dirname "$key_path")":/keys:ro \
  "$image" "$@"
