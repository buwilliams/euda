"""
Centralized Logger - JSONL logging with daily rolling and auto-cleanup.

Provides structured logging to JSONL files with:
- Log levels (debug, info, warn, error)
- Daily log file rolling
- Automatic cleanup of logs older than retention period
- Thread-safe writes
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"

# Log levels (lower number = more verbose)
LOG_LEVELS = {
    "debug": 0,
    "info": 1,
    "warn": 2,
    "error": 3,
}

# Default config
DEFAULT_LOG_LEVEL = "info"
DEFAULT_RETENTION_DAYS = 31

# Cached config
_config_cache: dict = None
_config_lock = threading.Lock()


def _load_config() -> dict:
    """Load and cache logging config."""
    global _config_cache
    with _config_lock:
        if _config_cache is not None:
            return _config_cache

        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH) as f:
                    config = json.load(f)
                _config_cache = config.get("logging", {})
            except (json.JSONDecodeError, IOError):
                _config_cache = {}
        else:
            _config_cache = {}

        return _config_cache


def _get_log_level() -> int:
    """Get configured log level as integer."""
    config = _load_config()
    level_name = config.get("level", DEFAULT_LOG_LEVEL).lower()
    return LOG_LEVELS.get(level_name, LOG_LEVELS["info"])


def _get_retention_days() -> int:
    """Get configured retention days."""
    config = _load_config()
    return config.get("retention_days", DEFAULT_RETENTION_DAYS)


def invalidate_config():
    """Invalidate cached config. Call when settings change."""
    global _config_cache
    with _config_lock:
        _config_cache = None


class Logger:
    """JSONL logger with daily rolling and auto-cleanup.

    Usage:
        logger = Logger("agents/friend/logs")
        logger.info({"event": "chat_start", "message_length": 100})

        # Or with singleton pattern:
        logger = get_logger("agents/friend/logs")
    """

    def __init__(self, base_path: str):
        """Initialize logger.

        Args:
            base_path: Path relative to data/ directory (without extension).
                      Daily files will be created as {base_path}/{date}.jsonl
        """
        self.base_path = DATA_DIR / base_path
        self._lock = threading.Lock()
        self._last_cleanup_date: Optional[str] = None

    def _get_log_file(self) -> Path:
        """Get today's log file path, creating directories if needed."""
        today = datetime.now().strftime("%Y-%m-%d")
        self.base_path.mkdir(parents=True, exist_ok=True)
        return self.base_path / f"{today}.jsonl"

    def _should_log(self, level: str) -> bool:
        """Check if message at given level should be logged."""
        msg_level = LOG_LEVELS.get(level.lower(), 0)
        configured_level = _get_log_level()
        return msg_level >= configured_level

    def _write(self, level: str, data: Dict[str, Any]):
        """Write a log entry if level passes filter."""
        if not self._should_log(level):
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            **data
        }

        with self._lock:
            log_file = self._get_log_file()
            with open(log_file, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")

            # Run cleanup once per day
            self._maybe_cleanup()

    def _maybe_cleanup(self):
        """Run cleanup if we haven't today."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._last_cleanup_date == today:
            return

        self._last_cleanup_date = today
        self._cleanup_old_logs()

    def _cleanup_old_logs(self):
        """Delete log files older than retention period."""
        retention_days = _get_retention_days()
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        if not self.base_path.exists():
            return

        for log_file in self.base_path.glob("*.jsonl"):
            # Parse date from filename (YYYY-MM-DD.jsonl)
            try:
                date_str = log_file.stem
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < cutoff_date:
                    log_file.unlink()
            except (ValueError, OSError):
                # Skip files that don't match expected format
                pass

    def debug(self, data: Dict[str, Any]):
        """Log at debug level."""
        self._write("debug", data)

    def info(self, data: Dict[str, Any]):
        """Log at info level."""
        self._write("info", data)

    def warn(self, data: Dict[str, Any]):
        """Log at warn level."""
        self._write("warn", data)

    def error(self, data: Dict[str, Any]):
        """Log at error level."""
        self._write("error", data)

    def write_raw(self, data: Dict[str, Any]):
        """Write a raw entry without timestamp/level wrapper.

        Use this for logs that have their own format (e.g., cost tracking).
        Still benefits from daily rolling and auto-cleanup.
        """
        with self._lock:
            log_file = self._get_log_file()
            with open(log_file, "a") as f:
                f.write(json.dumps(data, default=str) + "\n")

            # Run cleanup once per day
            self._maybe_cleanup()

    def read_logs(self, days: int = 1) -> list:
        """Read log entries from the last N days.

        Args:
            days: Number of days to read (default 1 = today only)

        Returns:
            List of log entry dicts, oldest first
        """
        entries = []
        today = datetime.now()

        for i in range(days):
            date = today - timedelta(days=i)
            log_file = self.base_path / f"{date.strftime('%Y-%m-%d')}.jsonl"

            if log_file.exists():
                with open(log_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass

        # Sort by timestamp (oldest first)
        entries.sort(key=lambda x: x.get("timestamp", ""))
        return entries


# Singleton registry for loggers
_loggers: Dict[str, Logger] = {}
_loggers_lock = threading.Lock()


def get_logger(base_path: str) -> Logger:
    """Get or create a logger for the given path.

    Args:
        base_path: Path relative to data/ directory.
                  e.g., "agents/friend/logs" -> data/agents/friend/logs/{date}.jsonl

    Returns:
        Logger instance (cached, so same path returns same logger)
    """
    with _loggers_lock:
        if base_path not in _loggers:
            _loggers[base_path] = Logger(base_path)
        return _loggers[base_path]
