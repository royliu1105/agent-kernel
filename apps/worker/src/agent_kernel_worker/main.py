"""Agent Kernel worker entrypoint."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from kernel_providers import MockLLMProvider, OpenAIProvider, ReplayLLMProvider
from kernel_rag import create_rag_tool_registry
from kernel_runtime import ModelRouter, QueuedRunWorker, RunExecutionService, WorkerBatchResult
from kernel_storage import create_engine_for_url, create_session_factory

app = typer.Typer(
    add_completion=False,
    help="Execute queued Agent Kernel runs.",
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def cli(
    ctx: typer.Context,
    once: Annotated[
        bool,
        typer.Option("--once", help="Process queued runs once and exit."),
    ] = False,
    loop: Annotated[
        bool,
        typer.Option("--loop", help="Continuously poll and process queued runs."),
    ] = False,
    limit: Annotated[
        int,
        typer.Option("--limit", min=1, help="Maximum queued runs to process per pass."),
    ] = 100,
    poll_interval: Annotated[
        float,
        typer.Option("--poll-interval", min=0.1, help="Seconds between loop polling passes."),
    ] = 5.0,
) -> None:
    """Run the worker in one-shot or polling mode."""

    if ctx.invoked_subcommand is not None:
        return
    if once and loop:
        raise typer.BadParameter("Use either --once or --loop, not both.")
    if not once and not loop:
        typer.echo("agent-kernel-worker ready")
        return

    worker = _create_worker()
    if once:
        result = asyncio.run(worker.run_once(limit=limit))
        _echo_batch_result(result)
        return

    asyncio.run(_run_loop(worker=worker, limit=limit, poll_interval=poll_interval))


def main() -> None:
    """Console script entrypoint."""

    app()


def _create_worker() -> QueuedRunWorker:
    engine = create_engine_for_url()
    session_factory = create_session_factory(engine)
    router = ModelRouter(
        {
            "mock": MockLLMProvider(),
            "openai": OpenAIProvider(),
            "replay": ReplayLLMProvider(),
        }
    )
    execution_service = RunExecutionService(
        router=router,
        tool_registry=create_rag_tool_registry(session_factory=session_factory),
    )
    return QueuedRunWorker(session_factory=session_factory, execution_service=execution_service)


async def _run_loop(
    *,
    worker: QueuedRunWorker,
    limit: int,
    poll_interval: float,
) -> None:
    while True:
        result = await worker.run_once(limit=limit)
        _echo_batch_result(result)
        await asyncio.sleep(poll_interval)


def _echo_batch_result(result: WorkerBatchResult) -> None:
    typer.echo(
        " ".join(
            [
                f"processed={result.processed_count}",
                f"succeeded={result.succeeded_count}",
                f"failed={result.failed_count}",
            ]
        )
    )
