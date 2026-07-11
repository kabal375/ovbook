#!/usr/bin/env bash
# Shared config + helpers for OpenViking functionality tests.
#
# Sourced by every test_*.sh. These are black-box smoke tests that hit a
# running OpenViking server over REST — they do NOT test the ovbook converter.
#
# Requirements: curl, python3, and a reachable OpenViking server.
# Config via env (all optional, sane defaults for our vm-showcase deploy):
#   OV_URL        base URL              (default http://127.0.0.1:1933)
#   OV_KEY        user API key          (default: api_key from ~/.openviking/ovcli.conf)
#   OV_TEST_DIR   a resource directory  (default viking://resources/second-brain)
#   OV_TEST_FILE  a resource file        (default .../second-brain/CLAUDE.md)
#   OV_TEST_QUERY semantic query        (default about disks/snapshots)
#   OV_TEST_GREP  literal grep pattern  (default OpenViking)
#
# Exit codes (per test): 0 = PASS, 1 = FAIL, 2 = SKIP.

set -uo pipefail

OV_URL="${OV_URL:-http://127.0.0.1:1933}"
OV_TEST_DIR="${OV_TEST_DIR:-viking://resources/second-brain}"
OV_TEST_FILE="${OV_TEST_FILE:-viking://resources/second-brain/CLAUDE.md}"
OV_TEST_QUERY="${OV_TEST_QUERY:-облачная платформа диски снапшоты}"
OV_TEST_GREP="${OV_TEST_GREP:-OpenViking}"

# SOCKS/HTTP proxies break curl→localhost — clear them.
unset ALL_PROXY HTTP_PROXY HTTPS_PROXY http_proxy https_proxy 2>/dev/null || true

# Resolve API key: env OV_KEY wins, else user key from ovcli.conf.
if [ -z "${OV_KEY:-}" ]; then
  OV_KEY="$(python3 - <<'PY' 2>/dev/null
import json, os
try:
    print(json.load(open(os.path.expanduser("~/.openviking/ovcli.conf"))).get("api_key", ""))
except Exception:
    print("")
PY
)"
fi

ov_get()  { curl -s --noproxy '*' -H "Authorization: Bearer ${OV_KEY}" "${OV_URL}$1"; }
ov_post() { curl -s --noproxy '*' -H "Authorization: Bearer ${OV_KEY}" -H "Content-Type: application/json" -X POST -d "$2" "${OV_URL}$1"; }

# jassert '<python bool expr over `d`>'  — reads JSON from stdin, exit 0 if truthy.
# NB: script is passed via -c (not a heredoc) so stdin stays free for the piped JSON.
jassert() {
  python3 -c '
import json, sys
expr = sys.argv[1]
raw = sys.stdin.read()
try:
    d = json.loads(raw) if raw.strip() else {}
except Exception as e:
    print("  (invalid JSON: %s)" % e, file=sys.stderr)
    sys.exit(1)
try:
    sys.exit(0 if eval(expr) else 1)
except Exception as e:
    print("  (assert error: %s)" % e, file=sys.stderr)
    sys.exit(1)
' "$1"
}

# jshow '<python expr over `d`>'  — reads JSON from stdin, prints the value (for messages).
jshow() {
  python3 -c '
import json, sys
raw = sys.stdin.read()
try:
    d = json.loads(raw) if raw.strip() else {}
    print(eval(sys.argv[1]))
except Exception:
    print("")
' "$1"
}

pass() { echo "PASS: ${TEST_NAME:-$(basename "$0")}${1:+ — $1}"; exit 0; }
fail() { echo "FAIL: ${TEST_NAME:-$(basename "$0")}${1:+ — $1}"; exit 1; }
skip() { echo "SKIP: ${TEST_NAME:-$(basename "$0")}${1:+ — $1}"; exit 2; }

require_key() { [ -n "${OV_KEY:-}" ] || fail "no API key (set OV_KEY or ~/.openviking/ovcli.conf)"; }
