#!/usr/bin/env bash
# HEALTH: the configured (user) API key can reach tenant-scoped data APIs.
# In api_key mode a ROOT key is rejected here — this guards against a
# misconfigured key (regression seen when the MCP wrapper used the root key).
source "$(dirname "$0")/_lib.sh"
TEST_NAME="health/auth: user key reaches data API"

require_key
r=$(ov_post "/api/v1/search/find" '{"query":"ping","limit":1}')
if echo "$r" | jassert 'd.get("status")=="ok"'; then
  pass
else
  fail "data API denied (wrong key?): ${r:0:200}"
fi
