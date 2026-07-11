#!/usr/bin/env bash
# FUNC: content/read returns the full (L2) body of a file.
source "$(dirname "$0")/_lib.sh"
TEST_NAME="func/read: content/read returns body"

require_key
r=$(ov_get "/api/v1/content/read?uri=${OV_TEST_FILE}")
if echo "$r" | jassert 'd.get("status")=="ok" and isinstance(d.get("result"),str) and len(d["result"])>0'; then
  pass "$(echo "$r" | jshow 'len(d["result"])') chars from ${OV_TEST_FILE}"
else
  fail "empty read for ${OV_TEST_FILE}: ${r:0:200}"
fi
