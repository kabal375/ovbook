#!/usr/bin/env bash
# FUNC: content/abstract returns the L0 abstract (~100 tokens).
source "$(dirname "$0")/_lib.sh"
TEST_NAME="func/abstract: content/abstract returns L0"

require_key
r=$(ov_get "/api/v1/content/abstract?uri=${OV_TEST_FILE}")
if echo "$r" | jassert 'd.get("status")=="ok" and isinstance(d.get("result"),str) and len(d["result"])>0'; then
  pass "$(echo "$r" | jshow 'len(d["result"])') chars abstract of ${OV_TEST_FILE}"
else
  fail "empty abstract for ${OV_TEST_FILE}: ${r:0:200}"
fi
