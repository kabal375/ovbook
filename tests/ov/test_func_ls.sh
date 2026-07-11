#!/usr/bin/env bash
# FUNC: fs/ls lists a directory (returns a non-empty list of entries).
source "$(dirname "$0")/_lib.sh"
TEST_NAME="func/ls: fs/ls returns entries"

require_key
r=$(ov_get "/api/v1/fs/ls?uri=viking://resources/")
if echo "$r" | jassert 'd.get("status")=="ok" and isinstance(d.get("result"),list) and len(d["result"])>0'; then
  pass "$(echo "$r" | jshow 'len(d["result"])') entries under viking://resources/"
else
  fail "ls returned no entries: ${r:0:200}"
fi
