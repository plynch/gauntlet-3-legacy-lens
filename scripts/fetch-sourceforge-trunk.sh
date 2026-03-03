#!/usr/bin/env bash
set -euo pipefail

SOURCEFORGE_TREE_URL="https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/"
SOURCEFORGE_TARBALL_URL="https://sourceforge.net/p/gnucobol/code/HEAD/tarball"
DEFAULT_DEST_DIR="backend/data/corpus/sourceforge-trunk"
WORK_DIR="/tmp/legacylens-sourceforge"

DEST_DIR="${1:-$DEFAULT_DEST_DIR}"

mkdir -p "$WORK_DIR"
cookie_file="$WORK_DIR/sourceforge.cookies"
page_file="$WORK_DIR/sourceforge-tree.html"
archive_file="$WORK_DIR/sourceforge-trunk.tar.gz"
extract_dir="$WORK_DIR/sourceforge-trunk-extract"

echo "Fetching SourceForge trunk page..."
curl --retry 5 --retry-all-errors -sS -c "$cookie_file" "$SOURCEFORGE_TREE_URL" -o "$page_file"

csrf_token="$(
  grep -Eo 'name="_csrf_token" type="hidden" value="[^"]+"' "$page_file" \
    | sed -E 's/.*value="([^"]+)"/\1/' \
    | head -n 1
)"

if [[ -z "$csrf_token" ]]; then
  echo "Failed to parse SourceForge CSRF token from tree page."
  echo "Open $SOURCEFORGE_TREE_URL and download snapshot manually."
  exit 1
fi

echo "Downloading SourceForge trunk snapshot..."
curl --retry 5 --retry-all-errors -sS -L \
  -b "$cookie_file" \
  -c "$cookie_file" \
  -X POST \
  -d "path=/trunk" \
  -d "_csrf_token=$csrf_token" \
  "$SOURCEFORGE_TARBALL_URL" \
  -o "$archive_file"

mkdir -p "$extract_dir"
rm -rf "$extract_dir"/*
tar -xzf "$archive_file" -C "$extract_dir"

top_dir="$(find "$extract_dir" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
if [[ -z "$top_dir" ]]; then
  echo "Failed to extract snapshot archive."
  exit 1
fi

mkdir -p "$DEST_DIR"
rm -rf "$DEST_DIR"/*
cp -R "$top_dir"/. "$DEST_DIR"/

file_count="$(
  find "$DEST_DIR" -type f \( -name '*.cbl' -o -name '*.cob' -o -name '*.cpy' -o -name '*.copy' \) | wc -l | tr -d ' '
)"
loc_total="$(
  find "$DEST_DIR" -type f \( -name '*.cbl' -o -name '*.cob' -o -name '*.cpy' -o -name '*.copy' \) \
    -print0 \
    | xargs -0 wc -l \
    | tail -n 1 \
    | awk '{print $1}'
)"
bytes_total="$(
  find "$DEST_DIR" -type f \( -name '*.cbl' -o -name '*.cob' -o -name '*.cpy' -o -name '*.copy' \) \
    -print0 \
    | xargs -0 wc -c \
    | tail -n 1 \
    | awk '{print $1}'
)"

echo "SourceForge trunk synced to $DEST_DIR"
echo "COBOL files: $file_count"
echo "Total LOC: ${loc_total:-0}"
echo "Total bytes: ${bytes_total:-0}"
