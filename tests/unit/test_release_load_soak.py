import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "release_load_soak.py"
SPEC = importlib.util.spec_from_file_location("release_load_soak", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
release_load_soak = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release_load_soak
SPEC.loader.exec_module(release_load_soak)


@pytest.mark.asyncio
async def test_worker_burst_profile_processes_all_runs() -> None:
    report = await release_load_soak.run_worker_burst(
        release_load_soak.LoadSoakProfile(
            name="test",
            runs=5,
            batch_size=2,
            max_elapsed_ms=5_000,
        )
    )

    assert report.passed is True
    assert report.runs_requested == 5
    assert report.processed_count == 5
    assert report.succeeded_count == 5
    assert report.failed_count == 0
    assert report.remaining_queued_count == 0
