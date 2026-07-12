#!/usr/bin/env bash
# FUNC: semantic find (search/find) with target_uri scope returns ranked hits.
# Asserts vault hits arrive under `resources` — the shape a client must merge
# (resources + memories + skills). Guards the "find returns nothing" regression.
source "$(dirname "$0")/_lib.sh"
TEST_NAME="func/find: semantic find returns scoped hits"

require_key
body=$(python3 -c 'import json,sys;print(json.dumps({"query":sys.argv[1],"limit":3,"target_uri":sys.argv[2]}))' "$OV_TEST_QUERY" "${OV_TEST_DIR}/")
r=$(ov_post "/api/v1/search/find" "$body")
if echo "$r" | jassert 'd.get("status")=="ok" and d.get("result",{}).get("total",0)>=1 and len(d["result"].get("resources",[]))>0'; then
  pass "total=$(echo "$r" | jshow 'd["result"].get("total")') top=$(echo "$r" | jshow 'round(d["result"]["resources"][0].get("score",0),2)')"
else
  fail "no scoped results (target_uri broken? empty index?): ${r:0:220}"
fi
