#!/bin/sh
set -eu

API_BASE_URL="${VITE_API_BASE_URL:-}"
SOURCE_REPO_BASE_URL="${VITE_SOURCE_REPO_BASE_URL:-}"
ENABLE_INGEST_CONTROLS="${VITE_ENABLE_INGEST_CONTROLS:-}"

# Railway can wrap values in quotes; strip one matching pair.
case "$API_BASE_URL" in
  \"*\")
    API_BASE_URL="${API_BASE_URL#\"}"
    API_BASE_URL="${API_BASE_URL%\"}"
    ;;
  \'*\')
    API_BASE_URL="${API_BASE_URL#\'}"
    API_BASE_URL="${API_BASE_URL%\'}"
    ;;
esac

case "$SOURCE_REPO_BASE_URL" in
  \"*\")
    SOURCE_REPO_BASE_URL="${SOURCE_REPO_BASE_URL#\"}"
    SOURCE_REPO_BASE_URL="${SOURCE_REPO_BASE_URL%\"}"
    ;;
  \'*\')
    SOURCE_REPO_BASE_URL="${SOURCE_REPO_BASE_URL#\'}"
    SOURCE_REPO_BASE_URL="${SOURCE_REPO_BASE_URL%\'}"
    ;;
esac

case "$ENABLE_INGEST_CONTROLS" in
  \"*\")
    ENABLE_INGEST_CONTROLS="${ENABLE_INGEST_CONTROLS#\"}"
    ENABLE_INGEST_CONTROLS="${ENABLE_INGEST_CONTROLS%\"}"
    ;;
  \'*\')
    ENABLE_INGEST_CONTROLS="${ENABLE_INGEST_CONTROLS#\'}"
    ENABLE_INGEST_CONTROLS="${ENABLE_INGEST_CONTROLS%\'}"
    ;;
esac

ESCAPED_API_BASE_URL="$(printf '%s' "$API_BASE_URL" | sed 's/\\/\\\\/g; s/"/\\"/g')"
ESCAPED_SOURCE_REPO_BASE_URL="$(printf '%s' "$SOURCE_REPO_BASE_URL" | sed 's/\\/\\\\/g; s/"/\\"/g')"
ESCAPED_ENABLE_INGEST_CONTROLS="$(printf '%s' "$ENABLE_INGEST_CONTROLS" | sed 's/\\/\\\\/g; s/"/\\"/g')"

cat > /app/dist/config.js <<EOF
window.__APP_CONFIG__ = {
  API_BASE_URL: "${ESCAPED_API_BASE_URL}",
  SOURCE_REPO_BASE_URL: "${ESCAPED_SOURCE_REPO_BASE_URL}",
  ENABLE_INGEST_CONTROLS: "${ESCAPED_ENABLE_INGEST_CONTROLS}"
};
EOF

exec serve -s dist -l "${PORT:-4173}"
