"""Nextcloud WebDAV file operations."""

import re
from typing import Optional
from xml.etree import ElementTree as ET

from .client import NextcloudClient


def _parse_propfind_response(xml_data: bytes) -> list[dict]:
    """Parse WebDAV PROPFIND response XML.

    Args:
        xml_data: Raw XML response bytes

    Returns:
        List of file/folder info dicts
    """
    # WebDAV namespace
    DAV_NS = "{DAV:}"

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return []

    items = []
    for response in root.findall(f".//{DAV_NS}response"):
        href = response.findtext(f"{DAV_NS}href", "")
        propstat = response.find(f"{DAV_NS}propstat")
        if propstat is None:
            continue

        prop = propstat.find(f"{DAV_NS}prop")
        if prop is None:
            continue

        # Extract properties
        displayname = prop.findtext(f"{DAV_NS}displayname", "")
        content_type = prop.findtext(f"{DAV_NS}getcontenttype", "")
        content_length = prop.findtext(f"{DAV_NS}getcontentlength", "0")
        last_modified = prop.findtext(f"{DAV_NS}getlastmodified", "")
        resource_type = prop.find(f"{DAV_NS}resourcetype")

        is_folder = resource_type is not None and resource_type.find(f"{DAV_NS}collection") is not None

        # Get filename from href
        name = href.rstrip("/").split("/")[-1]
        if not name and displayname:
            name = displayname

        items.append({
            "name": name,
            "path": href,
            "type": "folder" if is_folder else "file",
            "size": int(content_length) if content_length else 0,
            "content_type": content_type,
            "last_modified": last_modified,
        })

    return items


def nc_list_files(path: str = "/", instance: Optional[str] = None) -> dict:
    """List files and folders at a path.

    Args:
        path: Directory path (default: root)
        instance: Nextcloud instance ID

    Returns:
        Dict with files list or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    # WebDAV path
    webdav_path = f"/remote.php/dav/files/{client.username}{path}"
    if not webdav_path.endswith("/"):
        webdav_path += "/"

    headers = {
        "Depth": "1",
        "Content-Type": "application/xml",
    }

    propfind_body = b'''<?xml version="1.0" encoding="UTF-8"?>
    <d:propfind xmlns:d="DAV:">
        <d:prop>
            <d:displayname/>
            <d:getcontenttype/>
            <d:getcontentlength/>
            <d:getlastmodified/>
            <d:resourcetype/>
        </d:prop>
    </d:propfind>'''

    try:
        status, body, _ = client.request(
            "PROPFIND", webdav_path, data=propfind_body, headers=headers
        )
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 404:
        return {"error": f"Path not found: {path}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status not in (200, 207):  # 207 is Multi-Status
        return {"error": f"Server returned status {status}"}

    items = _parse_propfind_response(body)

    # Filter out the directory itself (first item)
    files = [f for f in items if f["path"].rstrip("/") != webdav_path.rstrip("/")]

    return {
        "path": path,
        "instance": client.instance_id,
        "files": files,
        "count": len(files),
    }


def nc_read_file(path: str, instance: Optional[str] = None) -> dict:
    """Read a file's contents.

    Args:
        path: File path
        instance: Nextcloud instance ID

    Returns:
        Dict with content or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    webdav_path = f"/remote.php/dav/files/{client.username}{path}"

    try:
        status, body, headers = client.request("GET", webdav_path)
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 404:
        return {"error": f"File not found: {path}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status != 200:
        return {"error": f"Server returned status {status}"}

    content_type = headers.get("Content-Type", "application/octet-stream")

    # Try to decode text content
    if content_type.startswith("text/") or content_type in (
        "application/json", "application/xml", "application/javascript"
    ):
        try:
            content = body.decode("utf-8")
            return {
                "path": path,
                "instance": client.instance_id,
                "content": content,
                "content_type": content_type,
                "size": len(body),
            }
        except UnicodeDecodeError:
            pass

    # Binary file
    return {
        "path": path,
        "instance": client.instance_id,
        "content": None,
        "message": "Binary file - content not displayed",
        "content_type": content_type,
        "size": len(body),
    }


def nc_write_file(
    path: str,
    content: str,
    instance: Optional[str] = None
) -> dict:
    """Write content to a file.

    Args:
        path: File path
        content: Content to write
        instance: Nextcloud instance ID

    Returns:
        Dict with status or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    webdav_path = f"/remote.php/dav/files/{client.username}{path}"
    content_bytes = content.encode("utf-8")

    headers = {"Content-Type": "text/plain; charset=utf-8"}

    try:
        status, _, _ = client.request(
            "PUT", webdav_path, data=content_bytes, headers=headers
        )
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 401:
        return {"error": "Authentication failed"}
    if status not in (200, 201, 204):
        return {"error": f"Server returned status {status}"}

    return {
        "status": "created" if status == 201 else "updated",
        "path": path,
        "instance": client.instance_id,
        "size": len(content_bytes),
    }


def nc_delete_file(path: str, instance: Optional[str] = None) -> dict:
    """Delete a file or folder.

    Args:
        path: Path to delete
        instance: Nextcloud instance ID

    Returns:
        Dict with status or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    webdav_path = f"/remote.php/dav/files/{client.username}{path}"

    try:
        status, _, _ = client.request("DELETE", webdav_path)
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 404:
        return {"error": f"Path not found: {path}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status not in (200, 204):
        return {"error": f"Server returned status {status}"}

    return {
        "status": "deleted",
        "path": path,
        "instance": client.instance_id,
    }


def nc_create_folder(path: str, instance: Optional[str] = None) -> dict:
    """Create a folder.

    Args:
        path: Folder path to create
        instance: Nextcloud instance ID

    Returns:
        Dict with status or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    webdav_path = f"/remote.php/dav/files/{client.username}{path}"
    if not webdav_path.endswith("/"):
        webdav_path += "/"

    try:
        status, _, _ = client.request("MKCOL", webdav_path)
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 405:
        return {"error": f"Folder already exists: {path}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status == 409:
        return {"error": "Parent folder does not exist"}
    if status not in (200, 201):
        return {"error": f"Server returned status {status}"}

    return {
        "status": "created",
        "path": path,
        "instance": client.instance_id,
    }


def nc_move_file(
    source: str,
    destination: str,
    instance: Optional[str] = None
) -> dict:
    """Move or rename a file/folder.

    Args:
        source: Source path
        destination: Destination path
        instance: Nextcloud instance ID

    Returns:
        Dict with status or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    source_path = f"/remote.php/dav/files/{client.username}{source}"
    dest_path = f"/remote.php/dav/files/{client.username}{destination}"
    dest_url = f"{client.url}{dest_path}"

    headers = {"Destination": dest_url}

    try:
        status, _, _ = client.request("MOVE", source_path, headers=headers)
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 404:
        return {"error": f"Source not found: {source}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status == 412:
        return {"error": f"Destination already exists: {destination}"}
    if status not in (200, 201, 204):
        return {"error": f"Server returned status {status}"}

    return {
        "status": "moved",
        "source": source,
        "destination": destination,
        "instance": client.instance_id,
    }
