"""
Nextcloud Client - Multi-instance client factory.

Handles authentication and HTTP for multiple Nextcloud instances.
Credentials loaded from environment variables.
Configuration loaded from agent-lib/nextcloud/config.json.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
import requests
from requests.auth import HTTPBasicAuth


# Look for config in agent-lib first, then data/agents
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
AGENT_LIB_CONFIG = PROJECT_ROOT / "agent-lib" / "nextcloud" / "config.json"
AGENTS_CONFIG = PROJECT_ROOT / "data" / "agents" / "nextcloud" / "config.json"


class NextcloudConfigError(Exception):
    """Raised when Nextcloud configuration is missing or invalid."""
    pass


@dataclass
class NextcloudInstance:
    """Configuration for a single Nextcloud instance."""
    id: str
    display_name: str
    url: str
    username: str
    password: str


# Cached instances
_instances_cache: Dict[str, NextcloudInstance] = {}


def _load_config() -> dict:
    """Load Nextcloud configuration from agent config.

    Looks for config in:
    1. data/agents/nextcloud/config.json (user's instance)
    2. agent-lib/nextcloud/config.json (template)
    """
    config_path = None

    # Prefer user's agents directory
    if AGENTS_CONFIG.exists():
        config_path = AGENTS_CONFIG
    elif AGENT_LIB_CONFIG.exists():
        config_path = AGENT_LIB_CONFIG
    else:
        raise NextcloudConfigError(
            "Nextcloud agent not found. "
            "Copy agent-lib/nextcloud to data/agents/nextcloud and configure."
        )

    with open(config_path) as f:
        config = json.load(f)

    if "integration" not in config:
        raise NextcloudConfigError(
            "No 'integration' section in nextcloud agent config. "
            "Add integration.instances configuration."
        )

    return config["integration"]


def _get_password(instance_id: str) -> str:
    """Get password from environment variable."""
    env_key = f"NEXTCLOUD_{instance_id.upper()}_PASSWORD"
    password = os.environ.get(env_key)
    if not password:
        raise NextcloudConfigError(
            f"Missing environment variable {env_key} for Nextcloud instance '{instance_id}'. "
            f"Create an app password in Nextcloud Settings > Security > Devices & Sessions."
        )
    return password


def get_instance(instance_id: str = None) -> NextcloudInstance:
    """Get a Nextcloud instance by ID.

    Args:
        instance_id: Instance ID from config. If None, uses default_instance.

    Returns:
        NextcloudInstance with connection details

    Raises:
        NextcloudConfigError: If instance not found or credentials missing
    """
    global _instances_cache

    nc_config = _load_config()

    # Use default if not specified
    if instance_id is None:
        instance_id = nc_config.get("default_instance")
        if not instance_id:
            raise NextcloudConfigError(
                "No instance_id provided and no default_instance configured"
            )

    # Return cached instance
    if instance_id in _instances_cache:
        return _instances_cache[instance_id]

    # Load instance config
    instances = nc_config.get("instances", {})
    if instance_id not in instances:
        available = list(instances.keys())
        raise NextcloudConfigError(
            f"Unknown Nextcloud instance '{instance_id}'. Available: {available}"
        )

    inst_config = instances[instance_id]

    # Validate required fields
    if "url" not in inst_config:
        raise NextcloudConfigError(f"Instance '{instance_id}' missing 'url' field")
    if "username" not in inst_config:
        raise NextcloudConfigError(f"Instance '{instance_id}' missing 'username' field")

    # Create and cache instance
    instance = NextcloudInstance(
        id=instance_id,
        display_name=inst_config.get("display_name", instance_id),
        url=inst_config["url"].rstrip("/"),
        username=inst_config["username"],
        password=_get_password(instance_id)
    )
    _instances_cache[instance_id] = instance

    return instance


def list_instances() -> List[dict]:
    """List all configured Nextcloud instances.

    Returns:
        List of dicts with id and display_name (no credentials exposed)
    """
    try:
        nc_config = _load_config()
    except NextcloudConfigError:
        return []

    instances = nc_config.get("instances", {})
    default = nc_config.get("default_instance")

    return [
        {
            "id": inst_id,
            "display_name": inst.get("display_name", inst_id),
            "url": inst.get("url"),
            "is_default": inst_id == default
        }
        for inst_id, inst in instances.items()
    ]


def invalidate_cache():
    """Clear cached instances. Call when config changes."""
    global _instances_cache
    _instances_cache = {}


class NextcloudClient:
    """HTTP client for a specific Nextcloud instance.

    Handles authentication and common request patterns.
    """

    def __init__(self, instance: NextcloudInstance):
        self.instance = instance
        self.auth = HTTPBasicAuth(instance.username, instance.password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.timeout = 30

    @property
    def webdav_url(self) -> str:
        """Base URL for WebDAV files API."""
        return f"{self.instance.url}/remote.php/dav/files/{self.instance.username}"

    @property
    def caldav_url(self) -> str:
        """Base URL for CalDAV API."""
        return f"{self.instance.url}/remote.php/dav/calendars/{self.instance.username}"

    @property
    def deck_api_url(self) -> str:
        """Base URL for Deck REST API."""
        return f"{self.instance.url}/index.php/apps/deck/api/v1"

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make an authenticated request.

        Args:
            method: HTTP method (GET, PUT, DELETE, PROPFIND, etc.)
            url: Full URL
            **kwargs: Passed to requests

        Returns:
            Response object

        Raises:
            requests.RequestException: On network errors
        """
        kwargs.setdefault("timeout", self.timeout)
        return self.session.request(method, url, **kwargs)

    def webdav_request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make a WebDAV request to files endpoint.

        Args:
            method: HTTP method
            path: Path relative to user's files root
            **kwargs: Passed to request

        Returns:
            Response object
        """
        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path
        url = f"{self.webdav_url}{path}"
        return self.request(method, url, **kwargs)

    def caldav_request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make a CalDAV request.

        Args:
            method: HTTP method
            path: Path relative to user's calendars root
            **kwargs: Passed to request

        Returns:
            Response object
        """
        if not path.startswith("/"):
            path = "/" + path
        url = f"{self.caldav_url}{path}"
        return self.request(method, url, **kwargs)

    def deck_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make a Deck API request.

        Args:
            method: HTTP method
            endpoint: API endpoint (e.g., "/boards", "/boards/1/stacks")
            **kwargs: Passed to request

        Returns:
            Response object
        """
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        url = f"{self.deck_api_url}{endpoint}"

        # Deck API requires OCS headers
        headers = kwargs.pop("headers", {})
        headers["OCS-APIRequest"] = "true"
        headers["Content-Type"] = "application/json"

        return self.request(method, url, headers=headers, **kwargs)


def get_client(instance_id: str = None) -> NextcloudClient:
    """Get a NextcloudClient for the specified instance.

    Args:
        instance_id: Instance ID or None for default

    Returns:
        Configured NextcloudClient
    """
    instance = get_instance(instance_id)
    return NextcloudClient(instance)
