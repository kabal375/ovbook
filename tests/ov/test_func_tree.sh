#!/usr/bin/env bash
# FUNC: fs/tree returns a directory hierarchy (non-empty list).
source "$(dirname "$0")/_lib.sh"
TEST_NAME="func/tree: fs/tree returns hierarchy"

require_key
r=$(ov_get "/api/v1/fs/tree?uri=${OV_TEST_DIR}&depth=1")
if echo "$r" | jassert 'd.get("status")=="ok" and isinstance(d.get("result"),list) and len(d["result"])>0'; then
  pass "$(echo "$r" | jshow 'len(d["result"])') nodes in ${OV_TEST_DIR} (depth 1)"
else
  fail "tree empty for ${OV_TEST_DIR}: ${r:0:200}"
fi
