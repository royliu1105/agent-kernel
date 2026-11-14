# DeepSeek and Alibaba Embedding Pilot Profile

Status: **Implementation/local offline verification passed;
live calls, deployment and remote CI not accepted (2026-11-15)**.
See the [scoped contract](specs/pilot-provider-compatibility.md) and
[PV1 record](pilots/pv1-2026-11-15-runbook-assistant.md). The total planning ceiling
is USD 10. This work authorizes no spending, active-stack update or credential export.

## Configuration Contract

The generation route is `deepseek:deepseek-chat`. The prefix selects DeepSeek,
and the remaining model ID is sent unchanged. The adapter reuses Responses,
including native function calls, persisted continuation, usage, deadlines and
retry classification. It is not the reference project's Chat Completions client.
The default model remains mock; supplying credentials does not change it.

The saved `deepseek-chat` ID is not a live-verified model. Current
[DeepSeek documentation](https://api-docs.deepseek.com/guides/responses_api/)
lists newer Responses models. Do not silently remap it or fall back to a paid
alternative. A later explicitly authorized smoke must verify account access,
the requested/returned ID, actual output shape and approval continuation.
Only validated completed function/message/reasoning items are replayed; unknown
or incomplete tool history fails closed. No provider-side web tools are enabled.

Configuration template for a **later approved isolated Docker profile**, not a
command to start or reconfigure the active stack:

```dotenv
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
AGENT_KERNEL_EMBEDDING_PROVIDER=dashscope
DASHSCOPE_API_KEY=
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v3
DASHSCOPE_EMBEDDING_DIMENSIONS=1024
```

Keep keys in ignored private files/platform secrets, never public templates,
arguments, logs or `NEXT_PUBLIC_*` variables. API and Worker must receive the
same configuration; both default entry points construct the same model router
and embedding factory. The base Compose file forwards these variables, but
the local overlay explicitly clears all paid-provider keys and forces mock
embeddings. `make docker-up` does not activate this pilot profile.

## Reference Credential Mapping

The runtime never loads `resource/`. Before a later authorized activation,
prepare only the required dedicated values in an ignored private pilot config:

| Reference variable | Maintained variable | Boundary |
| --- | --- | --- |
| `OPENAI_API_KEY` for the saved DeepSeek endpoint | `DEEPSEEK_API_KEY` | Never send this key to the official OpenAI route |
| `OPENAI_BASE_URL` | `DEEPSEEK_BASE_URL` | Only `https://api.deepseek.com` with optional `/v1` |
| `OPENAI_MODEL` | Run model `deepseek:<saved model>` | Preserve selected ID; no implicit model switch |
| `EMBEDDING_API_KEY` | `DASHSCOPE_API_KEY` | Independent from both generation keys |
| `EMBEDDING_BASE_URL` | `DASHSCOPE_BASE_URL` | Official HTTPS compatible-mode endpoint only |
| `EMBEDDING_MODEL` | `DASHSCOPE_EMBEDDING_MODEL` | This bounded profile supports `text-embedding-v3` |
| No verified matching dimension | `DASHSCOPE_EMBEDDING_DIMENSIONS=1024` | Do not inherit a 1536-dimension default from another model |

Do not source the entire reference `.env`: it also contains unrelated runtime
settings. No keys were copied during implementation or used by tests.

DashScope permits the known Beijing/Singapore/Hong Kong service domains or
workspace-specific `*.{region}.maas.aliyuncs.com` hosts, with the exact
`/compatible-mode/v1` path. URLs with embedded credentials, query strings,
fragments, custom ports or unrelated hosts are rejected without echoing values.
Redirects are not followed. These are operator-owned settings, not Run input.

## Embedding and Storage Boundaries

`dashscope` is explicit opt-in; keys alone leave the mock backend selected.
V3 defaults to 1024 dimensions and supports the documented 64/128/256/512/768/1024
configuration values. Account/region entitlement still requires live verification.
Inputs are split into batches of at most 10; returned indices, counts, vector
lengths and finite values use the existing validation. A failed batch returns
no partial result, and document indexing preserves the previous committed index.
The whole document can be retried later; earlier successful HTTP batches may
still have incurred charges. No free retry or invoice cap is claimed.
[Alibaba API contract](https://help.aliyun.com/zh/model-studio/embedding-interfaces-compatible-with-openai).

No migration or rewrite of current Docker vectors is performed. Use a fresh
isolated pilot knowledge base; never mix old OpenAI/mock vectors with v3 query
vectors. Native pgvector supports this dimension, but the existing HNSW
expression index targets 1536. A 1024-dimensional query is correct without a
matching index, not performance-certified; no new index is added in this scope.

## Readiness and Verification

`deepseek` readiness defaults to optional when its dedicated key is configured,
otherwise disabled; an operator can set `AGENT_KERNEL_READINESS_DEEPSEEK=required`.
`dashscope` readiness is required when that embedding backend is selected and
cannot be downgraded. `AGENT_KERNEL_READINESS_DASHSCOPE` can explicitly request
configuration checks otherwise. These checks create no HTTP requests and do
not establish balance, model availability or semantic quality. There are at most
eight bounded dependency probes; the mock default response stays unchanged.

The base Compose file does not forward `AGENT_KERNEL_READINESS_*` overrides.
For a later approved isolated Docker profile, explicitly set the desired values
under the API service's `environment` in its private Compose override. A root
`.env` or host export alone does not put these values inside the container.
Verify the effective container configuration before admitting the pilot; do not
alter the active local mock profile for this preparation.

Offline HTTP fixtures and disposable PostgreSQL tests cover routing, key/endpoint
isolation, retries, native multi-round approval/repeated resume, scoped access,
API indexing/query, Worker retrieval and rollback of failed reindex batches.
The actual evidence and remaining gates belong to the
[compatibility contract](specs/pilot-provider-compatibility.md#verification-gates).
Do not equate passing fixtures with PV3 live-model acceptance or PV5 user evidence.
