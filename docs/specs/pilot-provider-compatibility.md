# Pilot Provider Compatibility

Status: **Minimal implementation, local offline verification and reviewed
implementation-candidate CI passed; live compatibility/deployment pending (2026-11-15)**.
The maintainer selected the reference project's DeepSeek and Alibaba Cloud
Embedding services. This does not authorize paid requests, copying credentials,
active Docker updates, a new release, or other feature expansion. Budget remains
USD 10; current spending authorization is USD 0.

## Contract

- Add an explicit `deepseek:<model>` route with a dedicated `DEEPSEEK_API_KEY`.
  Reuse the maintained Responses serialization, native history, retries and
  approval checkpoints. Preserve provider identity across resume; reject history
  belonging to a different provider. No Chat Completions engine, automatic model
  remapping, thinking-mode control, server tools, streaming or fallback is added.
- Preserve the selected `deepseek-chat` identifier in the pilot instructions.
  Current official documentation advertises newer model IDs; no offline test
  proves that this saved identifier or account still works. A later authorized
  smoke must verify it; a rejection requires an explicit model decision.
- Add explicit `AGENT_KERNEL_EMBEDDING_PROVIDER=dashscope` with independent
  `DASHSCOPE_API_KEY`, endpoint, model and dimensions. Scope to `text-embedding-v3`,
  default 1024 dimensions. Index/query and API/Worker use the same factory.
  Split input into at most 10 texts per HTTP request; validate every response.
  A failed batch must not persist partial vectors.
- Only HTTPS official service endpoints are accepted for these named providers;
  reject credentials/query/fragment in URLs and unexpected hosts/paths. Do not
  redirect requests or infer a key from another provider's environment variable.
- Readiness validates configuration without calling models. Merely supplying a
  key does not enable paid indexing or change the default model. The local Docker
  profile continues clearing paid-provider keys and selecting mock embeddings.
- The maintained runtime never reads `resource/`. Later authorized activation
  requires privately mapping reference credentials to the dedicated variables.
  Neither model nor token bounds constitute a hard invoice cap.

## Design Sources

[DeepSeek Responses compatibility](https://api-docs.deepseek.com/guides/responses_api/)
documents stateless Responses, function calls and input/output token usage.
We retain the current strict native-item validator, including fail-closed handling
of unsupported/incomplete output. Reading a compatibility document is not live
continuation evidence.
[Alibaba Embedding compatibility](https://help.aliyun.com/zh/model-studio/embedding-interfaces-compatible-with-openai)
documents independent base URL/key/model, v3 dimensions and request limits.
Sources checked on 2026-11-15; no account was contacted.

## Verification Gates

- [x] Offline request/response, error classification and credential isolation.
- [x] Native multi-round approval/resume through Worker/default API composition.
- [x] Embedding batching, validation, API indexing/query and Worker retrieval.
- [x] Readiness and Compose/mock-default regression checks.
- [x] Python lint, typecheck, focused/full offline tests and documentation checks.
- [x] Reviewed implementation candidate verified by all four remote CI jobs.
- [ ] Separately authorized live model/account/embedding verification (not authorized).
- [ ] Separately authorized isolated pilot deployment (not authorized).

The first five gates establish implementation/offline compatibility only; remote
CI adds disposable-backend/deployment evidence. None completes PV1, CF2 or
live/user acceptance.

## Local Verification Evidence

Candidate: the uncommitted compatibility working tree on preparation baseline
`767e35af19d52d0596478af13d010ea2ba0ab45b` at the implementation checkpoint.
No new commit/push or remote CI was performed at that checkpoint. The subsequent
maintainer request authorizes review, commit/push and exact-candidate CI tracking;
see the [review record](../reviews/2026-11-15-pv1-provider-review.md).
Earlier CI does not verify this implementation. Paid calls and active Docker
updates remain prohibited.

Subsequent review reproduced and repaired non-finite/overflowing embedding-value
validation, then verified 1251 local tests (35 explicit skips) and exact candidate
`384416ce2f80538b4f3bffaf3806883deaf6d7fd` in
[CI 43622497986](https://github.com/royliu1105/agent-kernel/actions/runs/43622497986).
All four jobs passed. The [review record](../reviews/2026-11-15-pv1-provider-review.md)
contains final-tree evidence and the remaining live gates. The table below is
the earlier implementation checkpoint, not the final reviewed test count.

| Check | Observed result |
| --- | --- |
| Focused provider/embedding/router/retry/native continuation/readiness/local-default tests | 199 passed |
| Embedding bootstrap suite after adding second-batch failure persistence regression | 5 passed; native pgvector retained all 11 previous vectors and indexed status |
| Full `.venv/bin/pytest -q --tb=short` with disposable PostgreSQL and no live keys | 1232 passed, 35 opt-in skips, 236.98 seconds |
| `make release-eval` | RAG 3/3 and 4/4; tool evals 2/2; execution/backoff/native continuation/budget tests 72 passed; timeline 7/7 |
| `ruff check .`, `mypy .`, changed-file pre-commit hooks | Passed; mypy checked 237 source files |
| Documentation and new provider unit suite | 119 passed |
| Base and full local Compose `config --quiet` | Passed with synthetic values; no service startup or secret output |
| Parsed Compose regression with synthetic credentials | API/Worker match; local overlay clears OpenAI/DeepSeek/DashScope keys and selects mock |
| Disposable DB cleanup | Zero remaining `test_kernel_%` schemas; `make test-db-down` removed only the temporary test project |
| Active runtime | Read-only listing shows all 13 original `agent-kernel-local` services still running; no rebuild, restart, migration or business-data test was performed there |

The first DB attempt was blocked by the tool sandbox's loopback restriction;
the same offline tests then ran with authorized access to the disposable DB.
Integration tests exposed the old six-dependency readiness ceiling; it was
extended to the now-supported eight entries and verified before acceptance.
An initial test typing issue and Compose validation invocation missing synthetic
monitoring settings were corrected; the final checks above passed.

The 35 skips are explicit Docker-local/monitoring/full-observability/promtool,
backup drill, Redis/shared-admission and self-hosted deployment gates. No skipped
gate is reported passed. No Web change/browser test, real provider call, balance
query, actual credential loading/copy, live quality eval or pilot deployment was
performed. Existing active data and `resource/` were not modified.

Learning demonstrated: sharing a wire format does not make credentials or
provider-native continuation interchangeable. Tests inspect destination/auth
headers and independently persisted tool effects, not only an HTTP success.
This is assistant-led evidence, not an independent learner-proficiency claim.
