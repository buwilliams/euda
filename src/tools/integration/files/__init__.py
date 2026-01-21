"""
Store Module - Import files into long-term memory using RLM.

Provides bulk import of files with intelligent date extraction.
Files are processed through RLM which writes Python code to:
- Extract dates from content, filenames, or file metadata
- Format content for long-term memory storage
"""

from .loader import load_files, files_to_rlm_format, FileItem
from .rlm_processor import process_with_rlm, StoreResult, ProcessingResult
from .writer import write_to_memory
from .dedup import is_duplicate, record_processed, compute_hash

__all__ = [
    'load_files',
    'files_to_rlm_format',
    'FileItem',
    'process_with_rlm',
    'StoreResult',
    'ProcessingResult',
    'write_to_memory',
    'is_duplicate',
    'record_processed',
    'compute_hash',
]
