"""Agent Kernel worker entrypoint."""

from __future__ import annotations

import asyncio
import os
from typing import Annotated

import typer
from kernel_observability import (
    AggregatingMetricsRecorder,
    MetricsHttpServer,
    MetricsRecorder,
    configure_opentelemetry,
)
from kernel_providers import MockLLMProvider, OpenAIProvider, ReplayLLMProvider
from kernel_rag import create_rag_tool_registry
from kernel_runtime import (
    ModelRouter,
    QueuedRunWorker,
    RunExecutionService,
    StuckRunRecoveryBatchResult,
    StuckRunRecoveryService,
    WorkerBatchResult,
)
from kernel_runtime.queue import RunQueue
from kernel_runtime.redis_support import RedisSettings, create_redis_client, create_run_queue
from kernel_storage import create_engine_for_url, create_session_factory
from kernel_tools import ToolRegistry
from kernel_tools.external.config import external_tools_config_from_env
from kernel_tools.external.loader import load_external_tools
from sqlalchemy.orm import Session, sessionmaker

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
    recover_stuck: Annotated[
        bool,
        typer.Option("--recover-stuck", help="Recover runs with expired worker leases and exit."),
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
    selected_modes = sum(1 for selected in (once, loop, recover_stuck) if selected)
    if selected_modes > 1:
        raise typer.BadParameter("Use only one of --once, --loop, or --recover-stuck.")
    if not once and not loop and not recover_stuck:
        typer.echo("agent-kernel-worker ready")
        return

    configure_opentelemetry()
    engine = create_engine_for_url()
    session_factory = create_session_factory(engine)
    try:
        if recover_stuck:
            recovery_result = StuckRunRecoveryService(session_factory=session_factory).recover_once(
                limit=limit
            )
            _echo_recovery_result(recovery_result)
            return
        asyncio.run(
            _run_worker(
                session_factory=session_factory,
                once=once,
                limit=limit,
                poll_interval=poll_interval,
            )
        )
    finally:
        engine.dispose()


def main() -> None:
    """Console script entrypoint."""

    app()


def _create_worker(
    *,
    session_factory: sessionmaker[Session],
    registry: ToolRegistry | None = None,
    run_queue: RunQueue | None = None,
    metrics: MetricsRecorder | None = None,
) -> QueuedRunWorker:
    router = ModelRouter(
        {
            "mock": MockLLMProvider(),
            "openai": OpenAIProvider(),
            "replay": ReplayLLMProvider(),
        }
    )
    execution_service = RunExecutionService(
        router=router,
        tool_registry=registry or create_rag_tool_registry(session_factory=session_factory),
        metrics_recorder=metrics,
    )
    return QueuedRunWorker(
        session_factory=session_factory,
        execution_service=execution_service,
        run_queue=run_queue,
        metrics_recorder=metrics,
    )


async def _run_worker(
    *,
    session_factory: sessionmaker[Session],
    once: bool,
    limit: int,
    poll_interval: float,
) -> None:
    settings = RedisSettings.from_env()
    client = create_redis_client(settings) if settings.queue_backend == "redis" else None
    metrics = AggregatingMetricsRecorder()
    listener: MetricsHttpServer | None = None
    registry = create_rag_tool_registry(session_factory=session_factory)
    try:
        if os.getenv("AGENT_KERNEL_WORKER_METRICS_ENABLED", "false").lower() == "true":
            listener = MetricsHttpServer(
                metrics,
                host=os.getenv("AGENT_KERNEL_WORKER_METRICS_HOST", "127.0.0.1"),
                port=int(os.getenv("AGENT_KERNEL_WORKER_METRICS_PORT", "9001")),
                token=os.getenv("AGENT_KERNEL_MONITORING_TOKEN") or None,
            )
            listener.start()
        async with load_external_tools(registry, external_tools_config_from_env()):
            worker = _create_worker(
                session_factory=session_factory,
                registry=registry,
                run_queue=create_run_queue(settings, client=client),
                metrics=metrics,
            )
            if once:
                _echo_batch_result(await worker.run_once(limit=limit))
            else:
                await _run_loop(worker=worker, limit=limit, poll_interval=poll_interval)
    finally:
        if listener is not None:
            listener.close()
        if client is not None:
            client.close()


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


def _echo_recovery_result(result: StuckRunRecoveryBatchResult) -> None:
    typer.echo(
        " ".join(
            [
                f"inspected={result.inspected_count}",
                f"recovered={result.recovered_count}",
                f"skipped={result.skipped_count}",
            ]
        )
    )
