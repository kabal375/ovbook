#!/usr/bin/env bash
# FUNC: watch control plane (/watches) is queryable and returns the task list.
source "$(dirname "$0")/_lib.sh"
TEST_NAME="func/watches: watch list is queryable"

require_key
r=$(ov_get "/api/v1/watches")
if echo "$r" | jassert 'd.get("status")=="ok" and isinstance(d.get("result",{}).get("tasks"),list)'; then
  pass "$(echo "$r" | jshow 'd["result"].get("total", len(d["result"]["tasks"]))') watch task(s)"
else
  fail "watches endpoint malformed: ${r:0:200}"
fi
