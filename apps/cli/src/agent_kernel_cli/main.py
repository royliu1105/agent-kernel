"""Agent Kernel CLI entrypoint."""

from __future__ import annotations

from typing import Annotated

import typer

from agent_kernel_cli import __version__

app = typer.Typer(help="Agent Kernel developer CLI.")


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
