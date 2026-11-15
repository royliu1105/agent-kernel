"""Independent readback and key revocation inside the owned Web CI fixture."""

from __future__ import annotations

import json
import sys
from uuid import UUID

from cf2_runtime import guard
from cf2_scenario import lines, read, snapshot
from kernel_storage import ApiKeyRepository, create_engine_for_url
from sqlalchemy.orm import Session


def observe(run_id: str) -> dict[str, object]:
    UUID(run_id)
    data = snapshot(run_id, f"web-{run_id}")
    case = json.loads(data["run"]["input"]["task"])["case"]
    effects = [entry for entry in lines("effects.jsonl") if entry["item_id"] == case]
    requests = [entry for entry in lines("provider.jsonl") if entry["run_id"] == run_id]
    return {
        "status": data["run"]["status"],
        "calls": [
            {"status": call["status"], "approval_id": call["approval_id"]} for call in data["calls"]
        ],
        "effects": len(effects),
        "prompt_hashes": sorted({entry["prompt_sha256"] for entry in requests}),
        "provider_calls": len(requests),
        "output": data["run"]["output"],
    }


def revoke() -> dict[str, object]:
    engine = create_engine_for_url()
    try:
        with Session(engine) as session:
            repository = ApiKeyRepository(session)
            key = repository.authenticate(read("credentials.json")["operator"]["key"])
            assert key is not None and repository.revoke(key.id)
    finally:
        engine.dispose()
    return {"revoked": True}


if __name__ == "__main__":
    guard()
    command = sys.argv[1]
    if command == "observe":
        result = observe(sys.argv[2])
    elif command == "revoke":
        result = revoke()
    else:
        raise ValueError("Unknown observer command")
    print(json.dumps(result, sort_keys=True))
