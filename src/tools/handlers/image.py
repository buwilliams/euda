"""
Image file handler with EXIF extraction and vision processing support.
"""

import base64
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

from .base import FileHandler, register_handler

# Try to import PIL for image processing
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@register_handler
class ImageHandler(FileHandler):
    """Handler for image files with EXIF extraction."""

    categories = ["image"]

    # Vision API token cost is roughly fixed per image
    VISION_TOKENS_PER_IMAGE = 1500

    # Max dimension for resizing large images before encoding
    MAX_DIMENSION = 2048

    def extract_metadata(self, file_path: str) -> dict:
        """Extract image metadata including EXIF."""
        path = Path(file_path)
        stat = path.stat()

        metadata = {
            "type": "image",
            "size_bytes": stat.st_size,
            "extension": path.suffix.lower(),
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

        if not HAS_PIL:
            return metadata

        try:
            with Image.open(path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["format"] = img.format
                metadata["mode"] = img.mode

                # Extract EXIF data
                exif_data = self._extract_exif(img)
                if exif_data:
                    metadata["exif"] = exif_data

                    # Extract key temporal info
                    if "DateTimeOriginal" in exif_data:
                        metadata["date_taken"] = exif_data["DateTimeOriginal"]
                    elif "DateTime" in exif_data:
                        metadata["date_taken"] = exif_data["DateTime"]

                    # Extract GPS if available
                    if "GPSInfo" in exif_data:
                        metadata["has_gps"] = True

        except Exception as e:
            metadata["error"] = str(e)

        return metadata

    def _extract_exif(self, img: "Image.Image") -> dict:
        """Extract EXIF data from an image."""
        exif_data = {}

        try:
            raw_exif = img._getexif()
            if not raw_exif:
                return {}

            for tag_id, value in raw_exif.items():
                tag = TAGS.get(tag_id, tag_id)

                # Handle GPS data specially
                if tag == "GPSInfo":
                    gps_data = {}
                    for gps_tag_id, gps_value in value.items():
                        gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                        gps_data[gps_tag] = str(gps_value)
                    exif_data["GPSInfo"] = gps_data
                else:
                    # Convert to string for JSON serialization
                    try:
                        if isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        exif_data[tag] = str(value)
                    except Exception:
                        pass

        except Exception:
            pass

        return exif_data

    def prepare_for_ai(self, file_path: str, metadata: dict) -> str:
        """Prepare image for AI vision processing."""
        # Return a description with metadata that can be used
        # The actual image will be sent separately via vision API

        parts = [f"Image file: {Path(file_path).name}"]

        if "width" in metadata and "height" in metadata:
            parts.append(f"Dimensions: {metadata['width']}x{metadata['height']}")

        if "date_taken" in metadata:
            parts.append(f"Date taken: {metadata['date_taken']}")

        if metadata.get("has_gps"):
            parts.append("GPS data: available")

        # Include base64 encoded image for vision processing
        try:
            encoded = self.encode_for_vision(file_path)
            if encoded:
                parts.append(f"\n[Image data available for vision analysis]")
                # The actual base64 would be passed separately to the vision API
        except Exception as e:
            parts.append(f"Error encoding image: {e}")

        return "\n".join(parts)

    def encode_for_vision(self, file_path: str, max_size: int = 5_000_000) -> Optional[str]:
        """
        Encode image as base64 for vision API.

        Resizes if too large. Returns None if encoding fails.
        """
        if not HAS_PIL:
            # Fall back to direct encoding without resize
            with open(file_path, 'rb') as f:
                data = f.read()
                if len(data) > max_size:
                    return None
                return base64.b64encode(data).decode('utf-8')

        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # Resize if too large
                if max(img.width, img.height) > self.MAX_DIMENSION:
                    ratio = self.MAX_DIMENSION / max(img.width, img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                # Encode to JPEG
                import io
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                data = buffer.getvalue()

                if len(data) > max_size:
                    # Try lower quality
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=60)
                    data = buffer.getvalue()

                return base64.b64encode(data).decode('utf-8')

        except Exception:
            return None

    def estimate_tokens(self, metadata: dict) -> int:
        """Estimate tokens for image processing."""
        # Vision API has roughly fixed cost per image
        return self.VISION_TOKENS_PER_IMAGE

    def get_temporal_hints(self, file_path: str, metadata: dict) -> dict:
        """Extract temporal hints from image EXIF or filename."""
        # Priority 1: EXIF date
        if "date_taken" in metadata:
            try:
                # Parse EXIF date format: "2024:12:23 10:30:00"
                dt = datetime.strptime(metadata["date_taken"], "%Y:%m:%d %H:%M:%S")
                return {
                    "timestamp": dt.isoformat(),
                    "confidence": "high",
                    "source": "exif"
                }
            except ValueError:
                pass

        # Priority 2: Filename patterns
        filename = Path(file_path).stem
        timestamp = self._parse_filename_date(filename)
        if timestamp:
            return {
                "timestamp": timestamp,
                "confidence": "medium",
                "source": "filename"
            }

        # Priority 3: File modification time
        if "modified_time" in metadata:
            return {
                "timestamp": metadata["modified_time"],
                "confidence": "low",
                "source": "file_mtime"
            }

        return super().get_temporal_hints(file_path, metadata)

    def _parse_filename_date(self, filename: str) -> Optional[str]:
        """Try to parse date from common filename patterns."""
        patterns = [
            # IMG_20241223_103000
            (r'IMG_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})',
             lambda m: f"{m[1]}-{m[2]}-{m[3]}T{m[4]}:{m[5]}:{m[6]}"),
            # Screenshot 2024-12-23 at 10.30.00
            (r'Screenshot\s*(\d{4})-(\d{2})-(\d{2})\s*(?:at\s*)?(\d{1,2})\.(\d{2})\.(\d{2})',
             lambda m: f"{m[1]}-{m[2]}-{m[3]}T{m[4].zfill(2)}:{m[5]}:{m[6]}"),
            # 2024-12-23_103000 or 20241223_103000
            (r'(\d{4})-?(\d{2})-?(\d{2})[_\s](\d{2})(\d{2})(\d{2})',
             lambda m: f"{m[1]}-{m[2]}-{m[3]}T{m[4]}:{m[5]}:{m[6]}"),
            # Just date: 2024-12-23 or 20241223
            (r'^(\d{4})-?(\d{2})-?(\d{2})$',
             lambda m: f"{m[1]}-{m[2]}-{m[3]}T00:00:00"),
        ]

        for pattern, formatter in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    return formatter(match.groups())
                except Exception:
                    continue

        return None
