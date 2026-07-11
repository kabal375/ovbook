#!/usr/bin/env bash
# OpenViking functionality test runner.
#
# Usage: ./run.sh [SET]
#   SET = full       — every test_*.sh          (default)
#         health     — quick liveness (test_health_*.sh)
#         functions  — core API surface (test_func_*.sh)
#
# Config is via env vars read by _lib.sh (OV_URL, OV_KEY, OV_TEST_*).
# Each test script is standalone: one test == one script.
# Exit: 0 if all passed (skips allowed), 1 if any failed, 2 on bad usage.

set -uo pipefail
cd "$(dirname "$0")"

set_name="${1:-full}"
case "$set_name" in
  health)    pattern="test_health_*.sh" ;;
  functions) pattern="test_func_*.sh" ;;
  full)      pattern="test_*.sh" ;;
  -h|--help)
    grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//'
    exit 0 ;;
  *) echo "Unknown set: '$set_name' (use: full | health | functions)"; exit 2 ;;
esac

shopt -s nullglob
mapfile -t tests < <(printf '%s\n' $pattern | sort)
if [ "${#tests[@]}" -eq 0 ]; then
  echo "No tests match '$pattern'"; exit 2
fi

echo "== OpenViking tests — set '$set_name' (${#tests[@]} scripts) @ ${OV_URL:-http://127.0.0.1:1933} =="
p=0; f=0; s=0; failed=()
for t in "${tests[@]}"; do
  bash "$t"; rc=$?
  case "$rc" in
    0) p=$((p+1)) ;;
    2) s=$((s+1)) ;;
    *) f=$((f+1)); failed+=("$t") ;;
  esac
done

echo "-------------------------------------------------------------"
echo "PASS=$p  FAIL=$f  SKIP=$s  (total ${#tests[@]})"
if [ "$f" -ne 0 ]; then
  printf 'Failed: %s\n' "${failed[@]}"
  exit 1
fi
exit 0
