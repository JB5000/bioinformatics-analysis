#!/usr/bin/env bash
set -euo pipefail

echo "=== git status ==="
git status -sb

echo
printf "=== tracked files count ===\n"
git ls-files | wc -l

echo
printf "=== largest tracked files (top 10) ===\n"
git ls-files | xargs -I{} du -h "{}" 2>/dev/null | sort -hr | head -10
