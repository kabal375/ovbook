#!/usr/bin/env bash
# FUNC: glob (search/glob) resolves a filename pattern over a subtree.
source "$(dirname "$0")/_lib.sh"
TEST_NAME="func/glob: glob resolves file pattern"

require_key
body=$(python3 -c 'import json,sys;print(json.dumps({"pattern":"*.md","uri":sys.argv[1]}))' "${OV_TEST_DIR}/")
r=$(ov_post "/api/v1/search/glob" "$body")
# result may be a list of paths or a dict wrapping them — accept either, require non-empty.
if echo "$r" | jassert 'd.get("status")=="ok" and (len(d["result"])>0 if isinstance(d.get("result"),(list,dict)) else False)'; then
  pass "glob ok on ${OV_TEST_DIR}"
else
  fail "glob failed for *.md in ${OV_TEST_DIR}: ${r:0:200}"
fi
