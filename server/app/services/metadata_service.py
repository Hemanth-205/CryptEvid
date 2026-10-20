import os
import io
import re
import csv
import json
import zipfile
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ExifTags

class MetadataExtractionService:
    """
    Modular forensic metadata extraction service.
    Extracts structured technical attributes from evidence files safely without fabricating data.
    """

    @staticmethod
    def _convert_to_degrees(value) -> Optional[float]:
        """Helper function to convert GPS coordinates stored in EXIF to decimal degrees."""
        try:
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        except Exception:
            return None

    @classmethod
    def _extract_image_metadata(cls, file_bytes: bytes) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "media_type": "image",
            "width": None,
            "height": None,
            "format": None,
            "mode": None,
            "camera_make": None,
            "camera_model": None,
            "capture_timestamp": None,
            "latitude": None,
            "longitude": None,
            "exif_present": False
        }

        with Image.open(io.BytesIO(file_bytes)) as img:
            result["width"] = img.width
            result["height"] = img.height
            result["format"] = img.format
            result["mode"] = img.mode

            # Extract EXIF if available
            exif_data = img.getexif()
            if exif_data:
                result["exif_present"] = True
                exif_dict = {}
                for tag_id, value in exif_data.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    exif_dict[tag_name] = value

                result["camera_make"] = exif_dict.get("Make")
                result["camera_model"] = exif_dict.get("Model")
                result["capture_timestamp"] = exif_dict.get("DateTimeOriginal") or exif_dict.get("DateTime")

                # Check for GPS Info
                gps_info = exif_data.get_ifd(ExifTags.IFD.GPSInfo) if hasattr(exif_data, "get_ifd") else None
                if gps_info:
                    gps_dict = {}
                    for k, v in gps_info.items():
                        sub_tag = ExifTags.GPSTAGS.get(k, str(k))
                        gps_dict[sub_tag] = v

                    lat = gps_dict.get("GPSLatitude")
                    lat_ref = gps_dict.get("GPSLatitudeRef")
                    lon = gps_dict.get("GPSLongitude")
                    lon_ref = gps_dict.get("GPSLongitudeRef")

                    if lat and lat_ref:
                        decimal_lat = cls._convert_to_degrees(lat)
                        if decimal_lat is not None:
                            if str(lat_ref).upper() == "S":
                                decimal_lat = -decimal_lat
                            result["latitude"] = round(decimal_lat, 6)

                    if lon and lon_ref:
                        decimal_lon = cls._convert_to_degrees(lon)
                        if decimal_lon is not None:
                            if str(lon_ref).upper() == "W":
                                decimal_lon = -decimal_lon
                            result["longitude"] = round(decimal_lon, 6)

        return result

    @classmethod
    def _extract_pdf_metadata(cls, file_bytes: bytes) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "media_type": "pdf",
            "page_count": None,
            "author": None,
            "title": None,
            "creator": None,
            "creation_date": None,
            "pdf_version": None
        }

        # Header detection
        header = file_bytes[:1024].decode("latin-1", errors="ignore")
        v_match = re.search(r"%PDF-(\d+\.\d+)", header)
        if v_match:
            result["pdf_version"] = v_match.group(1)

        # Page count inspection
        # Look for occurrences of /Type /Page (excluding /Pages)
        content_str = file_bytes.decode("latin-1", errors="ignore")
        pages = re.findall(r"/Type\s*/Page\b", content_str)
        if pages:
            result["page_count"] = len(pages)
        else:
            # Fallback to /Count (\d+)
            count_match = re.search(r"/Count\s+(\d+)", content_str)
            if count_match:
                result["page_count"] = int(count_match.group(1))

        # Basic Info tags
        author_match = re.search(r"/Author\s*\(([^)]+)\)", content_str)
        if author_match:
            result["author"] = author_match.group(1)

        title_match = re.search(r"/Title\s*\(([^)]+)\)", content_str)
        if title_match:
            result["title"] = title_match.group(1)

        creator_match = re.search(r"/Creator\s*\(([^)]+)\)", content_str)
        if creator_match:
            result["creator"] = creator_match.group(1)

        creation_match = re.search(r"/CreationDate\s*\(([^)]+)\)", content_str)
        if creation_match:
            result["creation_date"] = creation_match.group(1)

        return result

    @classmethod
    def _extract_text_metadata(cls, file_bytes: bytes) -> Dict[str, Any]:
        text_content = ""
        encoding_used = "utf-8"
        try:
            text_content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text_content = file_bytes.decode("latin-1")
                encoding_used = "latin-1"
            except Exception:
                text_content = str(file_bytes)
                encoding_used = "binary_fallback"

        lines = text_content.splitlines()
        return {
            "media_type": "text",
            "line_count": len(lines),
            "character_count": len(text_content),
            "word_count": len(text_content.split()),
            "detected_encoding": encoding_used
        }

    @classmethod
    def _extract_csv_metadata(cls, file_bytes: bytes) -> Dict[str, Any]:
        text_content = ""
        for enc in ("utf-8", "latin-1"):
            try:
                text_content = file_bytes.decode(enc)
                break
            except Exception:
                continue

        lines = [line for line in text_content.splitlines() if line.strip()]
        row_count = len(lines)
        col_count = 0
        delimiter = ","

        if lines:
            try:
                sample = "\n".join(lines[:10])
                dialect = csv.Sniffer().sniff(sample)
                delimiter = dialect.delimiter
            except Exception:
                delimiter = ","

            reader = csv.reader(io.StringIO(lines[0]), delimiter=delimiter)
            first_row = next(reader, [])
            col_count = len(first_row)

        return {
            "media_type": "csv",
            "row_count": row_count,
            "column_count": col_count,
            "detected_delimiter": delimiter
        }

    @classmethod
    def _extract_json_metadata(cls, file_bytes: bytes) -> Dict[str, Any]:
        text_content = file_bytes.decode("utf-8", errors="replace")
        parsed = json.loads(text_content)
        is_dict = isinstance(parsed, dict)
        is_list = isinstance(parsed, list)

        return {
            "media_type": "json",
            "is_valid_json": True,
            "root_type": "object" if is_dict else "array" if is_list else "primitive",
            "key_count": len(parsed.keys()) if is_dict else None,
            "item_count": len(parsed) if is_list else None
        }

    @classmethod
    def _extract_zip_metadata(cls, file_bytes: bytes) -> Dict[str, Any]:
        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
            infolist = zf.infolist()
            total_uncompressed = sum(info.file_size for info in infolist)
            file_names = [info.filename for info in infolist[:20]]

            return {
                "media_type": "archive",
                "entry_count": len(infolist),
                "uncompressed_bytes": total_uncompressed,
                "is_encrypted": any(bool(info.flag_bits & 0x1) for info in infolist),
                "sample_entries": file_names
            }

    @classmethod
    def extract(cls, filename: str, file_bytes: bytes) -> Tuple[str, Dict[str, Any], Optional[float], Optional[float], Optional[str]]:
        """
        Main extraction entry point.
        Returns:
            (status: "EXTRACTED" | "FAILED",
             extracted_attributes: dict,
             latitude: float | None,
             longitude: float | None,
             error_message: str | None)
        """
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        attributes: Dict[str, Any] = {}
        latitude = None
        longitude = None
        error_msg = None
        status = "EXTRACTED"

        try:
            if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff"):
                attributes = cls._extract_image_metadata(file_bytes)
                latitude = attributes.get("latitude")
                longitude = attributes.get("longitude")

            elif ext == "pdf":
                attributes = cls._extract_pdf_metadata(file_bytes)

            elif ext in ("txt", "log"):
                attributes = cls._extract_text_metadata(file_bytes)

            elif ext == "csv":
                attributes = cls._extract_csv_metadata(file_bytes)

            elif ext == "json":
                attributes = cls._extract_json_metadata(file_bytes)

            elif ext in ("zip", "jar", "apk"):
                attributes = cls._extract_zip_metadata(file_bytes)

            else:
                attributes = {
                    "media_type": "generic_binary",
                    "file_extension": ext,
                    "byte_count": len(file_bytes)
                }

        except Exception as e:
            status = "FAILED"
            error_msg = f"Extraction failed for extension .{ext}: {str(e)}"
            attributes = {
                "error": str(e),
                "file_extension": ext,
                "byte_count": len(file_bytes)
            }

        return status, attributes, latitude, longitude, error_msg
