#!/usr/bin/env bash
# FUNC: fs/stat returns metadata for a resource directory.
source "$(dirname "$0")/_lib.sh"
TEST_NAME="func/stat: fs/stat returns metadata"

require_key
r=$(ov_get "/api/v1/fs/stat?uri=${OV_TEST_DIR}")
if echo "$r" | jassert 'd.get("status")=="ok" and d.get("result",{}).get("isDir") is True and "count" in d["result"]'; then
  pass "count=$(echo "$r" | jshow 'd["result"].get("count")') isLocked=$(echo "$r" | jshow 'd["result"].get("isLocked")')"
else
  fail "stat missing fields for ${OV_TEST_DIR}: ${r:0:200}"
fi
