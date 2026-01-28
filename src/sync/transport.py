"""
Transport - SSH/rsync transport layer for sync operations.

Handles SSH connectivity, file transfers, and remote command execution.
"""

import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple


DATA_DIR = Path(__file__).parent.parent.parent / "data"


@dataclass
class TransferResult:
    """Result of a file transfer operation."""
    success: bool
    files_transferred: int = 0
    bytes_transferred: int = 0
    error: Optional[str] = None


class Transport:
    """SSH/rsync transport for syncing with remote Euno instance."""

    def __init__(self, host: str, remote_path: str = "/opt/euno"):
        """
        Args:
            host: SSH host string (user@hostname or hostname)
            remote_path: Path to Euno installation on remote
        """
        self.host = host
        self.remote_path = remote_path
        self.remote_data_path = f"{remote_path}/data"

    def test_connection(self, timeout: int = 10) -> Tuple[bool, str]:
        """Test SSH connectivity.

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["ssh", "-o", f"ConnectTimeout={timeout}", self.host, "echo 'Connected'"],
                capture_output=True,
                text=True,
                timeout=timeout + 5,
            )
            if result.returncode == 0:
                return True, "Connected successfully"
            return False, result.stderr.strip() or "Connection failed"
        except subprocess.TimeoutExpired:
            return False, "Connection timed out"
        except Exception as e:
            return False, str(e)

    def run_remote_command(self, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        """Run a command on the remote server.

        Args:
            command: Shell command to execute
            timeout: Command timeout in seconds

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                ["ssh", self.host, command],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    def get_remote_instance_id(self) -> Optional[str]:
        """Get the remote instance's ID.

        Returns:
            Instance ID or None if not available
        """
        success, stdout, stderr = self.run_remote_command(
            f"cat {self.remote_data_path}/system/sync/state.json 2>/dev/null"
        )
        if success and stdout.strip():
            try:
                data = json.loads(stdout)
                return data.get("instance_id")
            except json.JSONDecodeError:
                pass
        return None

    def fetch_file(self, remote_relative_path: str, local_dest: Path) -> TransferResult:
        """Fetch a single file from remote.

        Args:
            remote_relative_path: Path relative to remote data directory
            local_dest: Local destination path

        Returns:
            TransferResult
        """
        remote_path = f"{self.remote_data_path}/{remote_relative_path}"
        local_dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = subprocess.run(
                ["rsync", "-az", f"{self.host}:{remote_path}", str(local_dest)],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return TransferResult(success=True, files_transferred=1)
            return TransferResult(success=False, error=result.stderr.strip())
        except Exception as e:
            return TransferResult(success=False, error=str(e))

    def push_file(self, local_path: Path, remote_relative_path: str) -> TransferResult:
        """Push a single file to remote.

        Args:
            local_path: Local file path
            remote_relative_path: Path relative to remote data directory

        Returns:
            TransferResult
        """
        if not local_path.exists():
            return TransferResult(success=False, error=f"Local file not found: {local_path}")

        remote_path = f"{self.remote_data_path}/{remote_relative_path}"

        # Ensure remote directory exists
        remote_dir = "/".join(remote_path.split("/")[:-1])
        self.run_remote_command(f"mkdir -p {remote_dir}")

        try:
            result = subprocess.run(
                ["rsync", "-az", str(local_path), f"{self.host}:{remote_path}"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return TransferResult(success=True, files_transferred=1)
            return TransferResult(success=False, error=result.stderr.strip())
        except Exception as e:
            return TransferResult(success=False, error=str(e))

    def fetch_directory(
        self,
        remote_relative_path: str,
        local_dest: Path,
        excludes: List[str] = None,
    ) -> TransferResult:
        """Fetch a directory from remote (non-destructive).

        Args:
            remote_relative_path: Path relative to remote data directory
            local_dest: Local destination directory
            excludes: Patterns to exclude

        Returns:
            TransferResult
        """
        remote_path = f"{self.remote_data_path}/{remote_relative_path}/"
        local_dest.mkdir(parents=True, exist_ok=True)

        cmd = ["rsync", "-az", "--itemize-changes"]
        for exc in (excludes or []):
            cmd.extend(["--exclude", exc])
        cmd.extend([f"{self.host}:{remote_path}", str(local_dest) + "/"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # Count transferred files from itemized output
                files = len([l for l in result.stdout.split("\n") if l.startswith("<") or l.startswith(">")])
                return TransferResult(success=True, files_transferred=files)
            return TransferResult(success=False, error=result.stderr.strip())
        except Exception as e:
            return TransferResult(success=False, error=str(e))

    def push_directory(
        self,
        local_path: Path,
        remote_relative_path: str,
        excludes: List[str] = None,
    ) -> TransferResult:
        """Push a directory to remote (non-destructive).

        Args:
            local_path: Local directory path
            remote_relative_path: Path relative to remote data directory
            excludes: Patterns to exclude

        Returns:
            TransferResult
        """
        if not local_path.exists():
            return TransferResult(success=False, error=f"Local directory not found: {local_path}")

        remote_path = f"{self.remote_data_path}/{remote_relative_path}/"

        # Ensure remote directory exists
        self.run_remote_command(f"mkdir -p {remote_path}")

        cmd = ["rsync", "-az", "--itemize-changes"]
        for exc in (excludes or []):
            cmd.extend(["--exclude", exc])
        cmd.extend([str(local_path) + "/", f"{self.host}:{remote_path}"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # Count transferred files from itemized output
                files = len([l for l in result.stdout.split("\n") if l.startswith("<") or l.startswith(">")])
                return TransferResult(success=True, files_transferred=files)
            return TransferResult(success=False, error=result.stderr.strip())
        except Exception as e:
            return TransferResult(success=False, error=str(e))

    def get_remote_file_content(self, remote_relative_path: str) -> Optional[str]:
        """Get content of a remote file.

        Args:
            remote_relative_path: Path relative to remote data directory

        Returns:
            File content or None if not found
        """
        remote_path = f"{self.remote_data_path}/{remote_relative_path}"
        success, stdout, _ = self.run_remote_command(f"cat {remote_path} 2>/dev/null")
        return stdout if success else None

    def get_remote_file_hash(self, remote_relative_path: str) -> Optional[str]:
        """Get SHA256 hash of a remote file.

        Args:
            remote_relative_path: Path relative to remote data directory

        Returns:
            Hash string or None if file not found
        """
        remote_path = f"{self.remote_data_path}/{remote_relative_path}"
        success, stdout, _ = self.run_remote_command(
            f"sha256sum {remote_path} 2>/dev/null | cut -d' ' -f1"
        )
        return stdout.strip() if success and stdout.strip() else None

    def list_remote_files(self, remote_relative_path: str, pattern: str = "*") -> List[str]:
        """List files in a remote directory.

        Args:
            remote_relative_path: Path relative to remote data directory
            pattern: Glob pattern (default: all files)

        Returns:
            List of filenames (not full paths)
        """
        remote_path = f"{self.remote_data_path}/{remote_relative_path}"
        success, stdout, _ = self.run_remote_command(
            f"ls -1 {remote_path}/{pattern} 2>/dev/null | xargs -n1 basename 2>/dev/null"
        )
        if success and stdout.strip():
            return [f for f in stdout.strip().split("\n") if f]
        return []

    def remote_file_exists(self, remote_relative_path: str) -> bool:
        """Check if a remote file exists.

        Args:
            remote_relative_path: Path relative to remote data directory

        Returns:
            True if file exists
        """
        remote_path = f"{self.remote_data_path}/{remote_relative_path}"
        success, _, _ = self.run_remote_command(f"test -f {remote_path}")
        return success

    def remote_directory_exists(self, remote_relative_path: str) -> bool:
        """Check if a remote directory exists.

        Args:
            remote_relative_path: Path relative to remote data directory

        Returns:
            True if directory exists
        """
        remote_path = f"{self.remote_data_path}/{remote_relative_path}"
        success, _, _ = self.run_remote_command(f"test -d {remote_path}")
        return success

    def fetch_to_temp(self, remote_relative_path: str) -> Optional[Path]:
        """Fetch a file to a temporary location.

        Args:
            remote_relative_path: Path relative to remote data directory

        Returns:
            Path to temporary file or None if fetch failed
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(remote_relative_path).suffix) as f:
            temp_path = Path(f.name)

        result = self.fetch_file(remote_relative_path, temp_path)
        if result.success:
            return temp_path
        temp_path.unlink(missing_ok=True)
        return None

    def backup_remote_data(self) -> Tuple[bool, str]:
        """Create a backup of the remote data directory.

        Creates a timestamped copy of the data directory on the remote server.

        Returns:
            Tuple of (success, backup_name or error message)
        """
        from datetime import datetime
        backup_name = f"data_backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        backup_path = f"{self.remote_path}/{backup_name}"

        success, stdout, stderr = self.run_remote_command(
            f"cd {self.remote_path} && if [ -d data ]; then cp -r data {backup_name}; echo 'OK'; else echo 'NO_DATA'; fi"
        )

        if success and "OK" in stdout:
            return True, backup_name
        elif success and "NO_DATA" in stdout:
            return True, ""  # No data to backup, that's OK
        else:
            return False, stderr or "Failed to create remote backup"


def backup_local_data() -> Tuple[bool, str]:
    """Create a backup of the local data directory.

    Creates a timestamped copy of the data directory.

    Returns:
        Tuple of (success, backup_name or error message)
    """
    import shutil
    from datetime import datetime

    if not DATA_DIR.exists():
        return True, ""  # No data to backup

    backup_name = f"data_backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup_path = DATA_DIR.parent / backup_name

    try:
        shutil.copytree(DATA_DIR, backup_path)
        return True, backup_name
    except Exception as e:
        return False, str(e)


def test_connection(host: str, timeout: int = 10) -> Tuple[bool, str]:
    """Test SSH connectivity to a host.

    Args:
        host: SSH host string
        timeout: Connection timeout

    Returns:
        Tuple of (success, message)
    """
    transport = Transport(host)
    return transport.test_connection(timeout)


def compute_file_hash(path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        path: File path

    Returns:
        Hash string
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
