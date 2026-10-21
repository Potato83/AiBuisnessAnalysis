#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:8080}"

curl --fail --silent --show-error "$BASE_URL/" | grep -q 'Alpha Business News Analytics'
curl --fail --silent --show-error "$BASE_URL/api/v1/health" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d=={"status":"ok","database":"ok"}, d'
curl --fail --silent --show-error "$BASE_URL/api/v1/companies" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); assert isinstance(d["items"],list) and isinstance(d["total"],int), d'
echo "SMOKE PASS: frontend -> API -> PostgreSQL"
