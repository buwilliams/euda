"""Web skill library."""

from .search import web_search
from .extract import extract_url, extract_urls
from .storage import load_watches, get_watch, add_watch, remove_watch, update_watch

__all__ = [
    "web_search",
    "extract_url",
    "extract_urls",
    "load_watches",
    "get_watch",
    "add_watch",
    "remove_watch",
    "update_watch",
]
