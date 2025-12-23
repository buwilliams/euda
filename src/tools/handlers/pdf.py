"""
PDF file handler with page-by-page processing for large documents.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from .base import FileHandler, register_handler

# Try to import pypdf for PDF processing
try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


@register_handler
class PDFHandler(FileHandler):
    """Handler for PDF files with large document support."""

    categories = ["pdf"]

    # Thresholds for large PDF handling
    FULL_PROCESSING_PAGES = 10  # Process fully if <= this many pages
    MAX_CONTENT_LENGTH = 100000  # Max chars to send to AI

    # Tokens per page estimate (average)
    TOKENS_PER_PAGE = 500

    def extract_metadata(self, file_path: str) -> dict:
        """Extract PDF metadata without reading full content."""
        path = Path(file_path)
        stat = path.stat()

        metadata = {
            "type": "pdf",
            "size_bytes": stat.st_size,
            "extension": ".pdf",
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

        if not HAS_PYPDF:
            metadata["error"] = "pypdf not installed"
            return metadata

        try:
            reader = PdfReader(path)
            metadata["page_count"] = len(reader.pages)

            # Extract document info
            info = reader.metadata
            if info:
                if info.title:
                    metadata["title"] = info.title
                if info.author:
                    metadata["author"] = info.author
                if info.subject:
                    metadata["subject"] = info.subject
                if info.creation_date:
                    metadata["creation_date"] = str(info.creation_date)

            # Try to extract table of contents
            toc = self._extract_toc(reader)
            if toc:
                metadata["toc"] = toc

            # Determine if this is a "large" PDF
            metadata["is_large"] = len(reader.pages) > self.FULL_PROCESSING_PAGES

        except Exception as e:
            metadata["error"] = str(e)

        return metadata

    def _extract_toc(self, reader: "PdfReader") -> list:
        """Extract table of contents/outline from PDF."""
        toc = []
        try:
            outlines = reader.outline
            if outlines:
                toc = self._flatten_outline(outlines)
        except Exception:
            pass
        return toc[:20]  # Limit to first 20 entries

    def _flatten_outline(self, outline, level: int = 0) -> list:
        """Flatten nested outline structure."""
        items = []
        for item in outline:
            if isinstance(item, list):
                items.extend(self._flatten_outline(item, level + 1))
            else:
                try:
                    title = item.title if hasattr(item, 'title') else str(item)
                    items.append({"level": level, "title": title})
                except Exception:
                    pass
        return items

    def prepare_for_ai(self, file_path: str, metadata: dict) -> str:
        """Prepare PDF content for AI processing."""
        if not HAS_PYPDF:
            return f"PDF file: {Path(file_path).name}\n[pypdf not installed, cannot extract text]"

        path = Path(file_path)
        parts = [f"PDF Document: {path.name}"]

        # Add metadata summary
        if "title" in metadata:
            parts.append(f"Title: {metadata['title']}")
        if "author" in metadata:
            parts.append(f"Author: {metadata['author']}")
        if "page_count" in metadata:
            parts.append(f"Pages: {metadata['page_count']}")

        # Add TOC if available
        if "toc" in metadata and metadata["toc"]:
            parts.append("\nTable of Contents:")
            for item in metadata["toc"][:10]:
                indent = "  " * item.get("level", 0)
                parts.append(f"{indent}- {item['title']}")

        parts.append("\n--- Content ---\n")

        try:
            reader = PdfReader(path)
            page_count = len(reader.pages)

            if page_count <= self.FULL_PROCESSING_PAGES:
                # Small PDF: extract all pages
                content = self._extract_all_pages(reader)
            else:
                # Large PDF: smart extraction
                content = self._extract_large_pdf(reader, metadata)

            parts.append(content)

        except Exception as e:
            parts.append(f"Error extracting content: {e}")

        result = "\n".join(parts)

        # Truncate if still too large
        if len(result) > self.MAX_CONTENT_LENGTH:
            half = self.MAX_CONTENT_LENGTH // 2
            result = (
                result[:half] +
                f"\n\n[... content truncated ({len(result)} chars total) ...]\n\n" +
                result[-half:]
            )

        return result

    def _extract_all_pages(self, reader: "PdfReader") -> str:
        """Extract text from all pages."""
        pages_text = []
        for i, page in enumerate(reader.pages, 1):
            try:
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(f"[Page {i}]\n{text}")
            except Exception:
                pages_text.append(f"[Page {i}]\n[Error extracting text]")
        return "\n\n".join(pages_text)

    def _extract_large_pdf(self, reader: "PdfReader", metadata: dict) -> str:
        """Smart extraction for large PDFs."""
        page_count = len(reader.pages)
        parts = []

        # First 3 pages (usually intro/abstract)
        parts.append("=== First Pages ===")
        for i in range(min(3, page_count)):
            try:
                text = reader.pages[i].extract_text() or ""
                if text.strip():
                    parts.append(f"[Page {i+1}]\n{text}")
            except Exception:
                pass

        # Middle pages - just headers/first lines
        if page_count > 6:
            parts.append(f"\n=== Middle Pages Summary (pages 4-{page_count-2}) ===")
            for i in range(3, page_count - 3):
                try:
                    text = reader.pages[i].extract_text() or ""
                    lines = text.strip().split('\n')
                    # Get first few non-empty lines (likely headers)
                    first_lines = [l.strip() for l in lines[:5] if l.strip()]
                    if first_lines:
                        parts.append(f"[Page {i+1}] {first_lines[0][:100]}...")
                except Exception:
                    pass

        # Last 3 pages (usually conclusions)
        if page_count > 3:
            parts.append("\n=== Last Pages ===")
            for i in range(max(3, page_count - 3), page_count):
                try:
                    text = reader.pages[i].extract_text() or ""
                    if text.strip():
                        parts.append(f"[Page {i+1}]\n{text}")
                except Exception:
                    pass

        return "\n".join(parts)

    def estimate_tokens(self, metadata: dict) -> int:
        """Estimate tokens for PDF processing."""
        page_count = metadata.get("page_count", 1)

        if page_count <= self.FULL_PROCESSING_PAGES:
            # Full processing
            return page_count * self.TOKENS_PER_PAGE
        else:
            # Large PDF: first 3 + summary + last 3
            # Plus overhead for structure
            return (6 * self.TOKENS_PER_PAGE) + (page_count * 20) + 500

    def get_temporal_hints(self, file_path: str, metadata: dict) -> dict:
        """Extract temporal hints from PDF."""
        # Priority 1: PDF creation date
        if "creation_date" in metadata:
            try:
                # PDF dates can be in various formats
                date_str = metadata["creation_date"]
                # Try to parse common formats
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y%m%d%H%M%S", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        dt = datetime.strptime(date_str[:19], fmt)
                        return {
                            "timestamp": dt.isoformat(),
                            "confidence": "high",
                            "source": "pdf_metadata"
                        }
                    except ValueError:
                        continue
            except Exception:
                pass

        # Priority 2: File modification time
        if "modified_time" in metadata:
            return {
                "timestamp": metadata["modified_time"],
                "confidence": "low",
                "source": "file_mtime"
            }

        return super().get_temporal_hints(file_path, metadata)
