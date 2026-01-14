"""
Nextcloud Files Tools - WebDAV file operations.
"""

import xml.etree.ElementTree as ET
from typing import List
import requests

from ... import tool
from .client import get_client, NextcloudConfigError


# WebDAV XML namespaces
DAV_NS = "{DAV:}"
OC_NS = "{http://owncloud.org/ns}"
NC_NS = "{http://nextcloud.org/ns}"


def _parse_propfind_response(xml_text: str, base_path: str) -> List[dict]:
    """Parse WebDAV PROPFIND XML response into file list.

    Args:
        xml_text: XML response body
        base_path: Base path to strip from hrefs

    Returns:
        List of file/folder dicts
    """
    root = ET.fromstring(xml_text)
    files = []

    for response in root.findall(f"{DAV_NS}response"):
        href_elem = response.find(f"{DAV_NS}href")
        if href_elem is None:
            continue

        href = href_elem.text or ""

        # Get properties from propstat
        propstat = response.find(f"{DAV_NS}propstat")
        if propstat is None:
            continue

        prop = propstat.find(f"{DAV_NS}prop")
        if prop is None:
            continue

        # Extract file info
        displayname = prop.find(f"{DAV_NS}displayname")
        contenttype = prop.find(f"{DAV_NS}getcontenttype")
        contentlength = prop.find(f"{DAV_NS}getcontentlength")
        lastmodified = prop.find(f"{DAV_NS}getlastmodified")
        resourcetype = prop.find(f"{DAV_NS}resourcetype")

        # Determine if folder
        is_folder = resourcetype is not None and resourcetype.find(f"{DAV_NS}collection") is not None

        # Extract path from href (remove base WebDAV path)
        path = href
        if "/remote.php/dav/files/" in path:
            # Extract just the path part after username
            parts = path.split("/remote.php/dav/files/")
            if len(parts) > 1:
                user_path = parts[1]
                # Remove username prefix
                if "/" in user_path:
                    path = "/" + "/".join(user_path.split("/")[1:])
                else:
                    path = "/"

        # Skip the base path itself (first entry)
        name = displayname.text if displayname is not None else path.rstrip("/").split("/")[-1]
        if not name or path.rstrip("/") == base_path.rstrip("/"):
            continue

        file_info = {
            "name": name,
            "path": path.rstrip("/") if not is_folder else path.rstrip("/") + "/",
            "type": "folder" if is_folder else "file",
        }

        if not is_folder:
            if contenttype is not None and contenttype.text:
                file_info["content_type"] = contenttype.text
            if contentlength is not None and contentlength.text:
                file_info["size"] = int(contentlength.text)

        if lastmodified is not None and lastmodified.text:
            file_info["last_modified"] = lastmodified.text

        files.append(file_info)

    return files


@tool(
    "nc_list_instances",
    "List configured Nextcloud server instances. Use when: checking available Nextcloud connections.",
    tool_type="integration"
)
def nc_list_instances() -> dict:
    """List all configured Nextcloud instances.

    Returns:
        Dict with instances list (no credentials exposed)
    """
    from .client import list_instances
    instances = list_instances()
    return {"instances": instances, "count": len(instances)}


@tool(
    "nc_list_files",
    "List files and folders in a Nextcloud directory. Use when: browsing cloud storage, finding files.",
    tool_type="integration"
)
def nc_list_files(path: str = "/", instance: str = None) -> dict:
    """List files and folders at a path.

    Args:
        path: Directory path (default: root "/")
        instance: Nextcloud instance ID (default: uses default_instance)

    Returns:
        Dict with files list or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    # Ensure path starts with /
    if not path.startswith("/"):
        path = "/" + path

    try:
        # WebDAV PROPFIND request
        resp = client.webdav_request(
            "PROPFIND",
            path,
            headers={"Depth": "1"}
        )

        if resp.status_code == 404:
            return {"error": f"Path not found: {path}"}
        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code not in (200, 207):
            return {"error": f"Request failed with status {resp.status_code}"}

        # Parse WebDAV XML response
        files = _parse_propfind_response(resp.text, path)
        return {
            "path": path,
            "files": files,
            "count": len(files),
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except ET.ParseError as e:
        return {"error": f"Failed to parse response: {str(e)}"}


@tool(
    "nc_read_file",
    "Read the contents of a text file from Nextcloud. Use when: viewing document contents.",
    tool_type="integration"
)
def nc_read_file(path: str, instance: str = None) -> dict:
    """Read a file's contents.

    Args:
        path: File path in Nextcloud
        instance: Nextcloud instance ID

    Returns:
        Dict with content or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    if not path.startswith("/"):
        path = "/" + path

    try:
        resp = client.webdav_request("GET", path)

        if resp.status_code == 404:
            return {"error": f"File not found: {path}"}
        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code != 200:
            return {"error": f"Request failed with status {resp.status_code}"}

        # Check content type - only return text content directly
        content_type = resp.headers.get("Content-Type", "")
        if "text" in content_type or "json" in content_type or "xml" in content_type:
            return {
                "path": path,
                "content": resp.text,
                "content_type": content_type,
                "size": len(resp.content),
                "instance": client.instance.display_name
            }
        else:
            return {
                "path": path,
                "content_type": content_type,
                "size": len(resp.content),
                "instance": client.instance.display_name,
                "message": "Binary file - content not displayed"
            }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}


@tool(
    "nc_write_file",
    "Create or update a file in Nextcloud. Use when: saving documents, creating notes.",
    tool_type="integration"
)
def nc_write_file(path: str, content: str, instance: str = None) -> dict:
    """Write content to a file.

    Args:
        path: File path to create/update
        content: File content (text)
        instance: Nextcloud instance ID

    Returns:
        Dict with status or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    if not path.startswith("/"):
        path = "/" + path

    try:
        resp = client.webdav_request(
            "PUT",
            path,
            data=content.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"}
        )

        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code == 409:
            return {"error": "Parent folder does not exist"}
        if resp.status_code not in (200, 201, 204):
            return {"error": f"Request failed with status {resp.status_code}"}

        return {
            "status": "created" if resp.status_code == 201 else "updated",
            "path": path,
            "size": len(content.encode("utf-8")),
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}


@tool(
    "nc_delete_file",
    "Delete a file or folder from Nextcloud. Use when: removing unwanted files.",
    tool_type="integration"
)
def nc_delete_file(path: str, instance: str = None) -> dict:
    """Delete a file or folder.

    Args:
        path: Path to delete
        instance: Nextcloud instance ID

    Returns:
        Dict with status or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    if not path.startswith("/"):
        path = "/" + path

    try:
        resp = client.webdav_request("DELETE", path)

        if resp.status_code == 404:
            return {"error": f"Path not found: {path}"}
        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code not in (200, 204):
            return {"error": f"Request failed with status {resp.status_code}"}

        return {
            "status": "deleted",
            "path": path,
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}


@tool(
    "nc_create_folder",
    "Create a new folder in Nextcloud. Use when: organizing files.",
    tool_type="integration"
)
def nc_create_folder(path: str, instance: str = None) -> dict:
    """Create a folder.

    Args:
        path: Folder path to create
        instance: Nextcloud instance ID

    Returns:
        Dict with status or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    if not path.startswith("/"):
        path = "/" + path

    try:
        resp = client.webdav_request("MKCOL", path)

        if resp.status_code == 405:
            return {"error": f"Folder already exists: {path}"}
        if resp.status_code == 409:
            return {"error": "Parent folder does not exist"}
        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code not in (200, 201):
            return {"error": f"Request failed with status {resp.status_code}"}

        return {
            "status": "created",
            "path": path,
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}


@tool(
    "nc_move_file",
    "Move or rename a file/folder in Nextcloud. Use when: reorganizing files.",
    tool_type="integration"
)
def nc_move_file(source: str, destination: str, instance: str = None) -> dict:
    """Move or rename a file/folder.

    Args:
        source: Current path
        destination: New path
        instance: Nextcloud instance ID

    Returns:
        Dict with status or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    if not source.startswith("/"):
        source = "/" + source
    if not destination.startswith("/"):
        destination = "/" + destination

    try:
        # WebDAV MOVE requires full destination URL
        dest_url = f"{client.webdav_url}{destination}"

        resp = client.webdav_request(
            "MOVE",
            source,
            headers={"Destination": dest_url}
        )

        if resp.status_code == 404:
            return {"error": f"Source not found: {source}"}
        if resp.status_code == 409:
            return {"error": "Destination parent folder does not exist"}
        if resp.status_code == 412:
            return {"error": "Destination already exists"}
        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code not in (200, 201, 204):
            return {"error": f"Request failed with status {resp.status_code}"}

        return {
            "status": "moved",
            "source": source,
            "destination": destination,
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
