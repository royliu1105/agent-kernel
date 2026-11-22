#!/bin/sh
# Mock troubleshooting demo: TraceId log MCP + fault KB search.
# Requires local-showcase overlay (make docker-showcase-up). No paid calls.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
STATE="$ROOT/.agent-kernel/showcase-evidence"
TOOLS="$ROOT/deploy/local-showcase-tools/tools.json"
DOC_OK="$ROOT/examples/docs/troubleshooting/redis-cart-timeout.md"
DOC_THIN="$ROOT/examples/docs/troubleshooting/insufficient-evidence.md"
TEMPLATE="$ROOT/docs/showcase/troubleshooting-evidence-template.json"

umask 077
mkdir -p "$STATE"
chmod 700 "$STATE"

cli() {
  sh "$ROOT/scripts/local-stack.sh" exec -T api agent-kernel "$@"
}

json_field() {
  python3 -c 'import json,sys; obj=json.loads(sys.argv[1]); print('"$2"')' "$1"
}

sha256_file() {
  python3 -c 'import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' "$1"
}

wait_status() {
  run_id=$1
  want=$2
  i=0
  while [ "$i" -lt 60 ]; do
    payload=$(cli run inspect "$run_id")
    status=$(json_field "$payload" 'obj["status"]')
    if [ "$status" = "$want" ]; then
      printf '%s\n' "$payload"
      return 0
    fi
    case "$status" in
      failed|canceled)
        printf 'Run reached terminal status %s before %s\n%s\n' "$status" "$want" "$payload" >&2
        exit 1
        ;;
      succeeded)
        if [ "$want" = "succeeded" ]; then
          printf '%s\n' "$payload"
          return 0
        fi
        printf 'Run succeeded before %s\n%s\n' "$want" "$payload" >&2
        exit 1
        ;;
    esac
    i=$((i + 1))
    sleep 1
  done
  printf 'Timed out waiting for run %s to reach %s\n' "$run_id" "$want" >&2
  exit 1
}

tool_structured() {
  python3 -c 'import json,sys
obj=json.loads(sys.argv[1])
data=obj["output"]["tool"]["result"]["data"]["structuredContent"]
print(json.dumps(data))' "$1"
}

printf 'Checking API CLI...\n'
if ! cli --help >/dev/null 2>&1; then
  printf 'API CLI unavailable. Start with: make docker-showcase-up\n' >&2
  exit 1
fi

printf 'Indexing troubleshooting runbooks...\n'
agent=$(cli agent create --name "Showcase Troubleshooting")
agent_id=$(json_field "$agent" 'obj["id"]')
kb=$(cli kb create --name "Showcase Troubleshooting KB")
kb_id=$(json_field "$kb" 'obj["id"]')

doc1=$(cli document upload "$kb_id" /app/examples/docs/troubleshooting/redis-cart-timeout.md)
doc1_id=$(json_field "$doc1" 'obj["id"]')
cli document ingest "$doc1_id" >/dev/null
cli document chunk "$doc1_id" >/dev/null
cli document index "$doc1_id" >/dev/null

doc2=$(cli document upload "$kb_id" /app/examples/docs/troubleshooting/insufficient-evidence.md)
doc2_id=$(json_field "$doc2" 'obj["id"]')
cli document ingest "$doc2_id" >/dev/null
cli document chunk "$doc2_id" >/dev/null
cli document index "$doc2_id" >/dev/null

search=$(cli kb search "$kb_id" --query "redis_timeout_checkout_cart" --top-k 3)
python3 -c 'import json,sys
rows=json.loads(sys.argv[1])["results"]
assert rows, "kb search empty for fingerprint"
blob=" ".join(r.get("content","") for r in rows)
assert "redis_timeout_checkout_cart" in blob
assert "insufficient" in blob.lower() or "Refuse" in blob or "evidence" in blob.lower()
' "$search"

printf 'TRACE-OK: explicit log tool run (read-only allow)...\n'
run_ok_input=$(python3 -c 'import json; print(json.dumps({
  "task":"Investigate checkout timeouts for TraceId TRACE-OK. Use log lookup then cite the runbook fingerprint.",
  "tool":{"name":"showcase_trace_logs","arguments":{"trace_id":"TRACE-OK"}},
}))')
run_ok=$(cli run create "$agent_id" --input "$run_ok_input")
run_ok_id=$(json_field "$run_ok" 'obj["id"]')
cli run queue "$run_ok_id" >/dev/null
ok_payload=$(wait_status "$run_ok_id" "succeeded")
ok_tool=$(tool_structured "$ok_payload")
python3 -c 'import json,sys
d=json.loads(sys.argv[1])
assert d.get("evidence_sufficient") is True
assert d.get("error_fingerprint")=="redis_timeout_checkout_cart"
assert d.get("trace_id")=="TRACE-OK"
assert any("redis-cart"==s.get("service") for s in d.get("spans") or [])
' "$ok_tool"

printf 'TRACE-THIN: insufficient evidence path...\n'
run_thin_input=$(python3 -c 'import json; print(json.dumps({
  "task":"Investigate TraceId TRACE-THIN. If logs are thin, refuse a root cause.",
  "tool":{"name":"showcase_trace_logs","arguments":{"trace_id":"TRACE-THIN"}},
}))')
run_thin=$(cli run create "$agent_id" --input "$run_thin_input")
run_thin_id=$(json_field "$run_thin" 'obj["id"]')
cli run queue "$run_thin_id" >/dev/null
thin_payload=$(wait_status "$run_thin_id" "succeeded")
thin_tool=$(tool_structured "$thin_payload")
python3 -c 'import json,sys
d=json.loads(sys.argv[1])
assert d.get("evidence_sufficient") is False
assert d.get("error_fingerprint") in (None, "")
assert "insufficient" in (d.get("refusal_hint") or "").lower() or "insufficient" in (d.get("summary") or "").lower()
' "$thin_tool"

stamp=$(date -u +%Y%m%dT%H%M%SZ)
out="$STATE/troubleshooting-evidence-$stamp.json"
python3 - <<PY
import hashlib, json, pathlib
template = json.loads(pathlib.Path("$TEMPLATE").read_text())
template["status"] = "executed_local_mock"
template["steps"] = {
    "docker_ready": True,
    "kb_indexed": True,
    "trace_ok_tool_succeeded": True,
    "trace_thin_refused_root_cause": True,
    "kb_fingerprint_hit": True,
}
template["ids"] = {
    "agent_id": "$agent_id",
    "knowledge_base_id": "$kb_id",
    "document_ids": ["$doc1_id", "$doc2_id"],
    "run_ok_id": "$run_ok_id",
    "run_thin_id": "$run_thin_id",
}
template["hashes"] = {
    "tools_config_sha256": "$(sha256_file "$TOOLS")",
    "redis_runbook_sha256": "$(sha256_file "$DOC_OK")",
    "insufficient_runbook_sha256": "$(sha256_file "$DOC_THIN")",
    "evidence_sha256": None,
}
template["observations"] = {
    "tool_name": "showcase_trace_logs",
    "trace_ok_fingerprint": "redis_timeout_checkout_cart",
    "trace_thin_evidence_sufficient": False,
    "paid_providers": False,
    "real_log_platform": False,
}
raw = json.dumps(template, indent=2, sort_keys=True) + "\n"
digest = hashlib.sha256(raw.encode()).hexdigest()
template["hashes"]["evidence_sha256"] = digest
path = pathlib.Path("$out")
path.write_text(json.dumps(template, indent=2, sort_keys=True) + "\n", encoding="utf-8")
path.chmod(0o600)
print(path)
print(digest)
PY

printf 'Troubleshooting mock demo succeeded.\n'
printf 'Evidence: %s\n' "$out"
printf 'This is local mock evidence, not a real log platform and not PV acceptance.\n'
