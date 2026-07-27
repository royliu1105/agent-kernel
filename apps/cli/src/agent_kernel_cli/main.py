"""Agent Kernel CLI entrypoint."""

from __future__ import annotations

import json
import os
from typing import Annotated
from uuid import UUID

import httpx
import typer
from click import ClickException

from agent_kernel_cli import __version__

app = typer.Typer(help="Agent Kernel developer CLI.")
agent_app = typer.Typer(help="Manage agents.")
run_app = typer.Typer(help="Manage runs.")

DEFAULT_API_URL = "http://127.0.0.1:8000"
API_URL_ENV = "AGENT_KERNEL_API_URL"


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"agent-kernel {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    """Manage Agent Kernel from the command line."""


@app.command()
def dev() -> None:
    """Print the Day 1 development placeholder."""

    typer.echo("Agent Kernel dev environment is ready.")


@agent_app.command("create")
def create_agent(
    name: Annotated[str, typer.Option("--name", help="Agent name.")],
    description: Annotated[
        str,
        typer.Option("--description", help="Agent description."),
    ] = "",
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Create an agent through the API."""

    response = _request_json(
        "POST",
        "/v1/agents",
        api_url=_resolve_api_url(api_url),
        json_payload={"name": name, "description": description},
    )
    _echo_json(response)


@run_app.command("create")
def create_run(
    agent_id: Annotated[UUID, typer.Argument(help="Agent ID.")],
    input_payload: Annotated[
        str,
        typer.Option("--input", help="Run input JSON object."),
    ] = "{}",
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Create a run for an agent through the API."""

    response = _request_json(
        "POST",
        f"/v1/agents/{agent_id}/runs",
        api_url=_resolve_api_url(api_url),
        json_payload={"input": _parse_json_object(input_payload)},
    )
    _echo_json(response)


@run_app.command("inspect")
def inspect_run(
    run_id: Annotated[UUID, typer.Argument(help="Run ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Inspect a run through the API."""

    response = _request_json("GET", f"/v1/runs/{run_id}", api_url=_resolve_api_url(api_url))
    _echo_json(response)


@run_app.command("events")
def list_run_events(
    run_id: Annotated[UUID, typer.Argument(help="Run ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """List run timeline events through the API."""

    response = _request_json(
        "GET",
        f"/v1/runs/{run_id}/events",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


@run_app.command("queue")
def queue_run(
    run_id: Annotated[UUID, typer.Argument(help="Run ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Queue a run for worker execution through the API."""

    response = _request_json(
        "POST",
        f"/v1/runs/{run_id}/queue",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


@run_app.command("cancel")
def cancel_run(
    run_id: Annotated[UUID, typer.Argument(help="Run ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Cancel a run through the API."""

    response = _request_json(
        "POST",
        f"/v1/runs/{run_id}/cancel",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


def _resolve_api_url(api_url: str) -> str:
    return os.getenv(API_URL_ENV, api_url).rstrip("/")


def _parse_json_object(value: str) -> dict[str, object]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise typer.BadParameter(f"Invalid JSON: {error.msg}") from error

    if not isinstance(parsed, dict):
        raise typer.BadParameter("Input must be a JSON object.")
    return parsed


def _request_json(
    method: str,
    path: str,
    *,
    api_url: str,
    json_payload: dict[str, object] | None = None,
) -> object:
    url = f"{api_url}{path}"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.request(method, url, json=json_payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as error:
        detail = _extract_error_detail(error.response)
        message = f"API returned {error.response.status_code}: {detail}"
        raise ClickException(message) from error
    except httpx.RequestError as error:
        raise ClickException(f"Could not reach Agent Kernel API: {error}") from error


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return response.text

    if isinstance(payload, dict) and "detail" in payload:
        return str(payload["detail"])
    return json.dumps(payload, sort_keys=True)


def _echo_json(payload: object) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


app.add_typer(agent_app, name="agent")
app.add_typer(run_app, name="run")
