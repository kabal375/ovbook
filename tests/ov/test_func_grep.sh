#!/usr/bin/env bash
# FUNC: grep (search/grep) finds a literal pattern; hits are under `matches`.
source "$(dirname "$0")/_lib.sh"
TEST_NAME="func/grep: content grep returns matches"

require_key
body=$(python3 -c 'import json,sys;print(json.dumps({"pattern":sys.argv[1],"uri":sys.argv[2]}))' "$OV_TEST_GREP" "$OV_TEST_FILE")
r=$(ov_post "/api/v1/search/grep" "$body")
if echo "$r" | jassert 'd.get("status")=="ok" and len(d.get("result",{}).get("matches",[]))>0'; then
  pass "$(echo "$r" | jshow 'len(d["result"]["matches"])') matches for /${OV_TEST_GREP}/"
else
  fail "no grep matches for /${OV_TEST_GREP}/ in ${OV_TEST_FILE}: ${r:0:200}"
fi
