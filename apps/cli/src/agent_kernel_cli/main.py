"""Agent Kernel CLI entrypoint."""

from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path
from typing import Annotated
from uuid import UUID

import httpx
import typer
from click import ClickException

from agent_kernel_cli import __version__

app = typer.Typer(help="Agent Kernel developer CLI.")
agent_app = typer.Typer(help="Manage agents.")
run_app = typer.Typer(help="Manage runs.")
approval_app = typer.Typer(help="Manage approvals.")
kb_app = typer.Typer(help="Manage knowledge bases.")
document_app = typer.Typer(help="Manage document metadata.")
ingestion_app = typer.Typer(help="Manage ingestion jobs.")
chunk_app = typer.Typer(help="Manage document chunks.")
embedding_app = typer.Typer(help="Manage chunk embeddings.")

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


@run_app.command("resume")
def resume_run(
    run_id: Annotated[UUID, typer.Argument(help="Run ID.")],
    approval_id: Annotated[
        UUID | None,
        typer.Option("--approval-id", help="Approval ID to resume from."),
    ] = None,
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Resume a waiting run through the API."""

    payload: dict[str, object] = {}
    if approval_id is not None:
        payload["approval_id"] = str(approval_id)
    response = _request_json(
        "POST",
        f"/v1/runs/{run_id}/resume",
        api_url=_resolve_api_url(api_url),
        json_payload=payload,
    )
    _echo_json(response)


@approval_app.command("list")
def list_approvals(
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """List approvals through the API."""

    response = _request_json("GET", "/v1/approvals", api_url=_resolve_api_url(api_url))
    _echo_json(response)


@approval_app.command("inspect")
def inspect_approval(
    approval_id: Annotated[UUID, typer.Argument(help="Approval ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Inspect one approval through the API."""

    response = _request_json(
        "GET",
        f"/v1/approvals/{approval_id}",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


@approval_app.command("approve")
def approve_approval(
    approval_id: Annotated[UUID, typer.Argument(help="Approval ID.")],
    decision_note: Annotated[
        str | None,
        typer.Option("--note", help="Optional approval decision note."),
    ] = None,
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Approve an approval through the API."""

    response = _request_json(
        "POST",
        f"/v1/approvals/{approval_id}/approve",
        api_url=_resolve_api_url(api_url),
        json_payload={"decision_note": decision_note},
    )
    _echo_json(response)


@approval_app.command("reject")
def reject_approval(
    approval_id: Annotated[UUID, typer.Argument(help="Approval ID.")],
    reason: Annotated[str, typer.Option("--reason", help="Rejection reason.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Reject an approval through the API."""

    response = _request_json(
        "POST",
        f"/v1/approvals/{approval_id}/reject",
        api_url=_resolve_api_url(api_url),
        json_payload={"reason": reason},
    )
    _echo_json(response)


@kb_app.command("create")
def create_knowledge_base(
    name: Annotated[str, typer.Option("--name", help="Knowledge base name.")],
    description: Annotated[
        str,
        typer.Option("--description", help="Knowledge base description."),
    ] = "",
    metadata: Annotated[
        str,
        typer.Option("--metadata", help="Knowledge base metadata JSON object."),
    ] = "{}",
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Create a knowledge base through the API."""

    response = _request_json(
        "POST",
        "/v1/knowledge-bases",
        api_url=_resolve_api_url(api_url),
        json_payload={
            "name": name,
            "description": description,
            "metadata": _parse_json_object(metadata),
        },
    )
    _echo_json(response)


@kb_app.command("list")
def list_knowledge_bases(
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """List knowledge bases through the API."""

    response = _request_json("GET", "/v1/knowledge-bases", api_url=_resolve_api_url(api_url))
    _echo_json(response)


@kb_app.command("inspect")
def inspect_knowledge_base(
    knowledge_base_id: Annotated[UUID, typer.Argument(help="Knowledge base ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Inspect one knowledge base through the API."""

    response = _request_json(
        "GET",
        f"/v1/knowledge-bases/{knowledge_base_id}",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


@document_app.command("register")
def register_document(
    knowledge_base_id: Annotated[UUID, typer.Argument(help="Knowledge base ID.")],
    title: Annotated[str, typer.Option("--title", help="Document title.")],
    source_uri: Annotated[str, typer.Option("--source-uri", help="Document source URI.")],
    mime_type: Annotated[
        str | None,
        typer.Option("--mime-type", help="Document MIME type."),
    ] = None,
    checksum: Annotated[
        str | None,
        typer.Option("--checksum", help="Document checksum."),
    ] = None,
    size_bytes: Annotated[
        int | None,
        typer.Option("--size-bytes", help="Document size in bytes."),
    ] = None,
    metadata: Annotated[
        str,
        typer.Option("--metadata", help="Document metadata JSON object."),
    ] = "{}",
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Register document metadata under a knowledge base through the API."""

    response = _request_json(
        "POST",
        f"/v1/knowledge-bases/{knowledge_base_id}/documents",
        api_url=_resolve_api_url(api_url),
        json_payload={
            "title": title,
            "source_uri": source_uri,
            "mime_type": mime_type,
            "checksum": checksum,
            "size_bytes": size_bytes,
            "metadata": _parse_json_object(metadata),
        },
    )
    _echo_json(response)


@document_app.command("upload")
def upload_document(
    knowledge_base_id: Annotated[UUID, typer.Argument(help="Knowledge base ID.")],
    file_path: Annotated[Path, typer.Argument(help="Path to the file to upload.")],
    title: Annotated[
        str | None,
        typer.Option("--title", help="Document title. Defaults to the file name."),
    ] = None,
    metadata: Annotated[
        str,
        typer.Option("--metadata", help="Document metadata JSON object."),
    ] = "{}",
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Upload a local file into a knowledge base through the API."""

    _parse_json_object(metadata)
    response = _request_file_json(
        "POST",
        f"/v1/knowledge-bases/{knowledge_base_id}/documents/upload",
        api_url=_resolve_api_url(api_url),
        file_path=file_path,
        data={
            "metadata": metadata,
            **({"title": title} if title is not None else {}),
        },
    )
    _echo_json(response)


@document_app.command("list")
def list_documents(
    knowledge_base_id: Annotated[UUID, typer.Argument(help="Knowledge base ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """List document metadata for a knowledge base through the API."""

    response = _request_json(
        "GET",
        f"/v1/knowledge-bases/{knowledge_base_id}/documents",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


@document_app.command("inspect")
def inspect_document(
    document_id: Annotated[UUID, typer.Argument(help="Document ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Inspect document metadata through the API."""

    response = _request_json(
        "GET",
        f"/v1/documents/{document_id}",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


@document_app.command("ingest")
def ingest_document(
    document_id: Annotated[UUID, typer.Argument(help="Document ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Ingest an uploaded document through the API."""

    response = _request_json(
        "POST",
        f"/v1/documents/{document_id}/ingest",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


@document_app.command("chunk")
def chunk_document(
    document_id: Annotated[UUID, typer.Argument(help="Document ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Chunk a parsed document through the API."""

    response = _request_json(
        "POST",
        f"/v1/documents/{document_id}/chunk",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


@document_app.command("index")
def index_document(
    document_id: Annotated[UUID, typer.Argument(help="Document ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Index a chunked document through the API."""

    response = _request_json(
        "POST",
        f"/v1/documents/{document_id}/index",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


@embedding_app.command("list")
def list_document_embeddings(
    document_id: Annotated[UUID, typer.Argument(help="Document ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """List chunk embeddings for a document through the API."""

    response = _request_json(
        "GET",
        f"/v1/documents/{document_id}/embeddings",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


@chunk_app.command("list")
def list_document_chunks(
    document_id: Annotated[UUID, typer.Argument(help="Document ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """List chunks for a document through the API."""

    response = _request_json(
        "GET",
        f"/v1/documents/{document_id}/chunks",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


@chunk_app.command("inspect")
def inspect_document_chunk(
    chunk_id: Annotated[UUID, typer.Argument(help="Document chunk ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Inspect one document chunk through the API."""

    response = _request_json(
        "GET",
        f"/v1/document-chunks/{chunk_id}",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


@ingestion_app.command("inspect")
def inspect_ingestion_job(
    job_id: Annotated[UUID, typer.Argument(help="Ingestion job ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """Inspect one ingestion job through the API."""

    response = _request_json(
        "GET",
        f"/v1/ingestion-jobs/{job_id}",
        api_url=_resolve_api_url(api_url),
    )
    _echo_json(response)


@ingestion_app.command("list")
def list_document_ingestion_jobs(
    document_id: Annotated[UUID, typer.Argument(help="Document ID.")],
    api_url: Annotated[
        str,
        typer.Option("--api-url", help="Agent Kernel API base URL."),
    ] = DEFAULT_API_URL,
) -> None:
    """List ingestion jobs for a document through the API."""

    response = _request_json(
        "GET",
        f"/v1/documents/{document_id}/ingestion-jobs",
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


def _request_file_json(
    method: str,
    path: str,
    *,
    api_url: str,
    file_path: Path,
    data: dict[str, str],
) -> object:
    if not file_path.is_file():
        raise ClickException(f"File does not exist: {file_path}")

    url = f"{api_url}{path}"
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    try:
        with httpx.Client(timeout=30.0) as client:
            with file_path.open("rb") as file:
                response = client.request(
                    method,
                    url,
                    data=data,
                    files={"file": (file_path.name, file, content_type)},
                )
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
app.add_typer(approval_app, name="approval")
app.add_typer(kb_app, name="kb")
app.add_typer(document_app, name="document")
app.add_typer(ingestion_app, name="ingestion")
app.add_typer(chunk_app, name="chunk")
app.add_typer(embedding_app, name="embedding")
