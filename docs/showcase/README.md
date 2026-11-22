# Local Mock Showcase

Operator-facing demos for **mature single-agent engineering** on the default
mock stack. These paths are **not** PV1–PV6 pilot acceptance and do not use
paid providers or real GitHub.

| Doc | Purpose |
| --- | --- |
| [Narrative](narrative.md) | Interview / operator talking points for the three demo beats |
| [Mock happy-path](mock-happy-path.md) | Docker → KB → memory → approval → resume → eval + pinned evidence |
| [Mock troubleshooting](troubleshooting-mock.md) | TraceId log MCP + fault KB + refuse-when-thin |
| [Evidence template](evidence-template.json) | Field skeleton filled by `scripts/showcase_mock_happy_path.sh` |
| [Troubleshooting evidence template](troubleshooting-evidence-template.json) | Filled by `scripts/showcase_troubleshooting_demo.sh` |
| [Clean-machine results (2026-11-22)](clean-machine-rehearsal-results.md) | Fresh-tree gates + showcase run evidence (not PV) |

Start the overlay with `make docker-showcase-up`, then `make showcase-happy-path`
and/or `make showcase-troubleshooting`.
Ordinary `make docker-up` does **not** load the showcase MCP tools.

Start with [narrative.md](narrative.md) if you need the story order; use the
happy-path for the hands-on mock demo. Paid DeepSeek + GitHub continuation is
recorded in [local-paid-experience.md](../local-paid-experience.md), separate
from this mock overlay.
