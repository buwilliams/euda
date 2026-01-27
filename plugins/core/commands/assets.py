"""Asset management commands for the core plugin."""

from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


def _get_assets_module():
    """Lazy import of assets module."""
    from src.core.data.assets import (
        list_assets, read_asset, write_asset, delete_asset
    )
    return {
        "list_assets": list_assets,
        "read_asset": read_asset,
        "write_asset": write_asset,
        "delete_asset": delete_asset,
    }


@app.command("list")
def list_cmd(topic_id: str = typer.Argument(..., help="Topic ID")):
    """List assets attached to a topic."""
    m = _get_assets_module()
    assets = m["list_assets"](topic_id)

    if not assets:
        print("No assets found.")
        return

    for asset in assets:
        filename = asset.get("filename", "?")
        size = asset.get("size", 0)
        mime = asset.get("mime_type") or "unknown"
        print(f"  {filename} ({size} bytes, {mime})")


@app.command("read")
def read_cmd(
    topic_id: str = typer.Argument(..., help="Topic ID"),
    filename: str = typer.Argument(..., help="Asset filename"),
):
    """Read an asset's content."""
    m = _get_assets_module()
    result = m["read_asset"](topic_id, filename)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    if result.get("content"):
        print(result["content"])
    elif result.get("note"):
        print(f"[{result.get('note')}]")
        print(f"Filename: {result.get('filename')}")
        print(f"Size: {result.get('size')} bytes")
        print(f"Type: {result.get('mime_type')}")


@app.command("write")
def write_cmd(
    topic_id: str = typer.Argument(..., help="Topic ID"),
    filename: str = typer.Argument(..., help="Asset filename"),
    content: str = typer.Argument(..., help="Content to write"),
):
    """Write content to an asset file."""
    m = _get_assets_module()
    result = m["write_asset"](topic_id, filename, content)

    print(f"Wrote {result.get('size', 0)} bytes to {filename}")


@app.command("delete")
def delete_cmd(
    topic_id: str = typer.Argument(..., help="Topic ID"),
    filename: str = typer.Argument(..., help="Asset filename"),
):
    """Delete an asset from a topic."""
    m = _get_assets_module()
    result = m["delete_asset"](topic_id, filename)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Deleted {filename}")
