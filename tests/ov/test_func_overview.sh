#!/usr/bin/env bash
# FUNC: content/overview returns the L1 summary (works on directories too).
source "$(dirname "$0")/_lib.sh"
TEST_NAME="func/overview: content/overview returns L1"

require_key
r=$(ov_get "/api/v1/content/overview?uri=${OV_TEST_DIR}")
if echo "$r" | jassert 'd.get("status")=="ok" and isinstance(d.get("result"),str) and len(d["result"])>0'; then
  pass "$(echo "$r" | jshow 'len(d["result"])') chars overview of ${OV_TEST_DIR}"
else
  fail "empty overview for ${OV_TEST_DIR}: ${r:0:200}"
fi
