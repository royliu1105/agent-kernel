"""Real pg_dump/pg_restore contract with matching local object manifest."""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "backend_drill", Path(__file__).parents[2] / "scripts" / "backend_drill.py"
)
assert SPEC is not None and SPEC.loader is not None
backend_drill = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = backend_drill
SPEC.loader.exec_module(backend_drill)


def test_postgresql_backup_restore_and_matching_object_manifest() -> None:
    url = os.environ.get("AGENT_KERNEL_TEST_POSTGRES_URL")
    if not url or os.environ.get("AGENT_KERNEL_ALLOW_BACKEND_DRILL") != "1":
        pytest.skip("Requires explicit disposable PostgreSQL service and backend drill opt-in.")
    report = backend_drill.run_backup_drill(
        url, pg_container=os.environ.get("AGENT_KERNEL_TEST_PG_TOOLS_CONTAINER")
    )
    assert report["passed"]
    assert report["objects_verified"] == 2
    assert report["pgvector_retrieval_verified"]
    assert report["execution_checkpoint_verified"]
    assert report["corruption_detected"]
