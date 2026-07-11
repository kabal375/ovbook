#!/usr/bin/env bash
# HEALTH: server is up and initialized.
source "$(dirname "$0")/_lib.sh"
TEST_NAME="health/server: /system/status initialized"

require_key
r=$(ov_get "/api/v1/system/status")
if echo "$r" | jassert 'd.get("status")=="ok" and d.get("result",{}).get("initialized") is True'; then
  pass "user=$(echo "$r" | jshow 'd["result"].get("user")')"
else
  fail "server not initialized: ${r:0:200}"
fi
