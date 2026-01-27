"""
Plugin Exceptions - Error types for the plugin system.
"""


class PluginError(Exception):
    """Base exception for plugin-related errors."""
    pass


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin doesn't exist."""
    pass


class PluginExecutionError(PluginError):
    """Raised when a plugin command fails to execute."""
    pass


class PluginTimeoutError(PluginError):
    """Raised when a plugin execution times out."""
    pass


class PluginValidationError(PluginError):
    """Raised when a plugin fails validation."""
    pass
