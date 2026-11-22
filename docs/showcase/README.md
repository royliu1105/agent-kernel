# Local Mock Showcase

Operator-facing demos for **mature single-agent engineering** on the default
mock stack. These paths are **not** PV1–PV6 pilot acceptance and do not use
paid providers or real GitHub.

| Doc | Purpose |
| --- | --- |
| [Mock happy-path](mock-happy-path.md) | Docker → KB → memory → approval → resume → eval + pinned evidence |
| [Evidence template](evidence-template.json) | Field skeleton filled by `scripts/showcase_mock_happy_path.sh` |
| [Clean-machine results (2026-11-22)](clean-machine-rehearsal-results.md) | Fresh-tree gates + showcase run evidence (not PV) |

Start the overlay with `make docker-showcase-up`, then `make showcase-happy-path`.
Ordinary `make docker-up` does **not** load the showcase MCP tool.
