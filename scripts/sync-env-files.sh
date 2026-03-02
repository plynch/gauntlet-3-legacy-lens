#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

copy_example() {
  local example_path="$1"
  local env_path="$2"

  if [[ ! -f "$ROOT_DIR/$example_path" ]]; then
    echo "Missing example file: $example_path" >&2
    exit 1
  fi

  cp "$ROOT_DIR/$example_path" "$ROOT_DIR/$env_path"
  echo "Wrote $env_path from $example_path"
}

copy_example "backend/.env.staging.example" "backend/.env.staging"
copy_example "backend/.env.production.example" "backend/.env.production"
copy_example "frontend/.env.staging.example" "frontend/.env.staging"
copy_example "frontend/.env.production.example" "frontend/.env.production"
