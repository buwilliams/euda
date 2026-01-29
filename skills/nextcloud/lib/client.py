"""Nextcloud base client and configuration."""

import json
import os
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error
import base64


def _get_config_path() -> Path:
    """Get path to system config file."""
    data_dir = os.environ.get("EUNO_DATA_DIR")
    if data_dir:
        return Path(data_dir) / "system" / "config.json"
    return Path(__file__).parent.parent.parent.parent / "data" / "system" / "config.json"


def _load_config() -> dict:
    """Load system configuration."""
    config_path = _get_config_path()
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}


def list_instances() -> list[dict]:
    """List configured Nextcloud instances.

    Returns:
        List of instance configs with id, name, url
    """
    config = _load_config()
    nc_config = config.get("nextcloud", {})
    instances = nc_config.get("instances", [])

    return [
        {
            "id": inst.get("id"),
            "name": inst.get("name", inst.get("id")),
            "url": inst.get("url"),
        }
        for inst in instances
    ]


def get_instance_config(instance_id: Optional[str] = None) -> Optional[dict]:
    """Get configuration for a specific Nextcloud instance.

    Args:
        instance_id: Instance ID. If None, returns first/default instance.

    Returns:
        Instance config dict or None if not found
    """
    config = _load_config()
    nc_config = config.get("nextcloud", {})
    instances = nc_config.get("instances", [])

    if not instances:
        return None

    if instance_id is None:
        # Return first instance as default
        return instances[0]

    for inst in instances:
        if inst.get("id") == instance_id:
            return inst

    return None


class NextcloudClient:
    """Base client for Nextcloud API requests."""

    def __init__(self, instance_id: Optional[str] = None):
        """Initialize Nextcloud client.

        Args:
            instance_id: Nextcloud instance ID. Uses default if None.

        Raises:
            ValueError: If no instance configured or instance not found
        """
        config = get_instance_config(instance_id)
        if config is None:
            if instance_id:
                raise ValueError(f"Nextcloud instance '{instance_id}' not found")
            raise ValueError("No Nextcloud instances configured")

        self.instance_id = config.get("id")
        self.url = config.get("url", "").rstrip("/")
        self.username = config.get("username")
        self.password = config.get("password")

        if not self.url:
            raise ValueError(f"Nextcloud instance '{self.instance_id}' has no URL")

    def _get_auth_header(self) -> str:
        """Get Basic auth header value."""
        if not self.username or not self.password:
            return ""
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def request(
        self,
        method: str,
        path: str,
        data: Optional[bytes] = None,
        headers: Optional[dict] = None,
        timeout: int = 30
    ) -> tuple[int, bytes, dict]:
        """Make an authenticated request to the Nextcloud server.

        Args:
            method: HTTP method (GET, PUT, DELETE, MKCOL, MOVE, PROPFIND)
            path: URL path (will be joined with instance URL)
            data: Request body bytes
            headers: Additional headers
            timeout: Request timeout in seconds

        Returns:
            Tuple of (status_code, response_body, response_headers)
        """
        url = f"{self.url}{path}"
        req_headers = headers or {}

        auth = self._get_auth_header()
        if auth:
            req_headers["Authorization"] = auth

        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return (
                    response.status,
                    response.read(),
                    dict(response.headers),
                )
        except urllib.error.HTTPError as e:
            return (e.code, e.read(), dict(e.headers))
        except urllib.error.URLError as e:
            raise ConnectionError(f"Could not connect to {self.url}: {e.reason}")
