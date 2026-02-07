"""CLI — init, serve, status."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click

from engram.config import Config
from engram.storage.sqlite_store import SQLiteStore


@click.group()
@click.version_option(package_name="engram-ai")
def main() -> None:
    """Engram — your AI's persistent memory."""


@main.command()
@click.argument("path", type=click.Path(), default="~/engram")
def init(path: str) -> None:
    """Initialize a new engram workspace."""
    workspace = Path(path).expanduser().resolve()

    async def _init() -> None:
        config = Config(workspace_path=workspace)
        store = SQLiteStore(workspace / "engram.db")
        await store.initialize()
        await store.close()
        config.save()

    asyncio.run(_init())
    click.echo(f"Initialized workspace at {workspace}")
    click.echo(f"Database: {workspace / 'engram.db'}")
    click.echo("Add to Claude Desktop config:")
    click.echo(f'  "engram": {{"command": "engram", "args": ["serve", "{workspace}"]}}')


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--transport", type=click.Choice(["stdio"]), default="stdio")
def serve(path: str, transport: str) -> None:
    """Start the MCP server."""
    workspace = Path(path).expanduser().resolve()
    db_path = workspace / "engram.db"

    if not db_path.exists():
        click.echo(f"Error: No database at {db_path}. Run 'engram init' first.", err=True)
        sys.exit(1)

    from engram.server import create_server

    server = create_server(str(db_path))
    server.run(transport=transport)  # type: ignore[arg-type]


@main.command()
@click.argument("path", type=click.Path(exists=True))
def status(path: str) -> None:
    """Show workspace status."""
    workspace = Path(path).expanduser().resolve()
    db_path = workspace / "engram.db"

    if not db_path.exists():
        click.echo(f"Error: No database at {db_path}", err=True)
        sys.exit(1)

    async def _status() -> dict:
        store = SQLiteStore(db_path)
        await store.initialize()
        stats = await store.get_stats()
        await store.close()
        return stats

    stats = asyncio.run(_status())
    click.echo(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
