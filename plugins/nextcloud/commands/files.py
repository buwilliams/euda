"""Nextcloud file operations for the nextcloud plugin."""

from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


def _get_files_module():
    """Lazy import of nextcloud files module."""
    from src.tools.integration.nextcloud.files import (
        nc_list_files, nc_read_file, nc_write_file,
        nc_delete_file, nc_create_folder, nc_move_file
    )
    return {
        "nc_list_files": nc_list_files,
        "nc_read_file": nc_read_file,
        "nc_write_file": nc_write_file,
        "nc_delete_file": nc_delete_file,
        "nc_create_folder": nc_create_folder,
        "nc_move_file": nc_move_file,
    }


@app.command("list")
def list_cmd(
    path: str = typer.Argument("/", help="Directory path (default: root)"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """List files and folders at a path."""
    m = _get_files_module()
    result = m["nc_list_files"](path=path, instance=instance)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Path: {result.get('path')}")
    print(f"Instance: {result.get('instance')}")
    print(f"Files ({result.get('count', 0)}):")

    for f in result.get("files", []):
        ftype = f.get("type", "file")
        name = f.get("name", "?")
        if ftype == "folder":
            print(f"  [DIR] {name}/")
        else:
            size = f.get("size", 0)
            print(f"  {name} ({size} bytes)")


@app.command("read")
def read_cmd(
    path: str = typer.Argument(..., help="File path"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """Read a file's contents."""
    m = _get_files_module()
    result = m["nc_read_file"](path=path, instance=instance)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    if result.get("content"):
        print(result["content"])
    else:
        print(f"[{result.get('message', 'Binary file')}]")
        print(f"Path: {result.get('path')}")
        print(f"Type: {result.get('content_type')}")
        print(f"Size: {result.get('size')} bytes")


@app.command("write")
def write_cmd(
    path: str = typer.Argument(..., help="File path"),
    content: str = typer.Argument(..., help="Content to write"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """Write content to a file."""
    m = _get_files_module()
    result = m["nc_write_file"](path=path, content=content, instance=instance)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Status: {result.get('status')}")
    print(f"Path: {result.get('path')}")
    print(f"Size: {result.get('size')} bytes")


@app.command("delete")
def delete_cmd(
    path: str = typer.Argument(..., help="Path to delete"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """Delete a file or folder."""
    m = _get_files_module()
    result = m["nc_delete_file"](path=path, instance=instance)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Deleted: {result.get('path')}")


@app.command("mkdir")
def mkdir_cmd(
    path: str = typer.Argument(..., help="Folder path to create"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """Create a folder."""
    m = _get_files_module()
    result = m["nc_create_folder"](path=path, instance=instance)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Created folder: {result.get('path')}")


@app.command("move")
def move_cmd(
    source: str = typer.Argument(..., help="Source path"),
    destination: str = typer.Argument(..., help="Destination path"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """Move or rename a file/folder."""
    m = _get_files_module()
    result = m["nc_move_file"](source=source, destination=destination, instance=instance)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Moved: {result.get('source')} -> {result.get('destination')}")
