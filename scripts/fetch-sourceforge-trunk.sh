#!/usr/bin/env bash
set -euo pipefail

SOURCEFORGE_TREE_URL="https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/"
SOURCEFORGE_SVN_URL="https://svn.code.sf.net/p/gnucobol/code/trunk"
DEFAULT_DEST_DIR="backend/data/corpus/sourceforge-trunk"

DEST_DIR="${1:-$DEFAULT_DEST_DIR}"
WORK_DIR="$(mktemp -d /tmp/legacylens-sourceforge.XXXXXX)"
trap 'rm -rf "$WORK_DIR"' EXIT

if ! command -v svn >/dev/null 2>&1; then
  echo "Missing dependency: svn"
  echo "Install Subversion and rerun. macOS example: brew install subversion"
  exit 1
fi

echo "Source of truth: $SOURCEFORGE_TREE_URL"
echo "Running svn export..."
svn export --force "$SOURCEFORGE_SVN_URL" "$WORK_DIR/trunk"

mkdir -p "$DEST_DIR"
rm -rf "$DEST_DIR"/*
cp -R "$WORK_DIR/trunk"/. "$DEST_DIR"/

file_count="$(find "$DEST_DIR" -type f \( -name '*.cbl' -o -name '*.cob' -o -name '*.cpy' -o -name '*.copy' \) | wc -l | tr -d ' ')"

if [[ "$file_count" -eq 0 ]]; then
  loc_total=0
  bytes_total=0
else
  loc_total="$(
    find "$DEST_DIR" -type f \( -name '*.cbl' -o -name '*.cob' -o -name '*.cpy' -o -name '*.copy' \) \
      -print0 | xargs -0 wc -l | tail -n 1 | awk '{print $1}'
  )"
  bytes_total="$(
    find "$DEST_DIR" -type f \( -name '*.cbl' -o -name '*.cob' -o -name '*.cpy' -o -name '*.copy' \) \
      -print0 | xargs -0 wc -c | tail -n 1 | awk '{print $1}'
  )"
fi

echo "Synced into $DEST_DIR"
echo "COBOL files: $file_count"
echo "Total LOC: ${loc_total:-0}"
echo "Total bytes: ${bytes_total:-0}"
