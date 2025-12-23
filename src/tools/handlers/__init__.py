"""
File handlers for the Ingestion Agent.

Each handler knows how to:
1. Extract metadata from a file type (without loading full content)
2. Prepare content for AI processing
3. Estimate token usage
"""

from .base import FileHandler, get_handler
from .text import TextHandler
from .image import ImageHandler
from .pdf import PDFHandler

__all__ = [
    'FileHandler',
    'get_handler',
    'TextHandler',
    'ImageHandler',
    'PDFHandler',
]
