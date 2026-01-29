"""Web search library functions."""

from .search import web_search
from .extract import extract_url, extract_urls

__all__ = ["web_search", "extract_url", "extract_urls"]
