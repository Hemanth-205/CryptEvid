import hashlib
from typing import Tuple, BinaryIO

class HashService:
    """
    Modular cryptographic hash engine for digital forensics.
    Implements chunk-based streaming SHA-256 calculation to support large forensic disk images
    and evidence dumps without loading entire files into memory.
    """
    DEFAULT_CHUNK_SIZE = 64 * 1024  # 64 KB

    @classmethod
    def calculate_sha256_file(cls, file_path: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
        """
        Calculate SHA-256 hash of a file on disk by reading in chunks.
        Scalable for multi-gigabyte evidence files.
        """
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest().lower()

    @classmethod
    def calculate_sha256_stream(cls, stream: BinaryIO, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
        """
        Calculate SHA-256 hash from an open binary file-like stream.
        """
        hasher = hashlib.sha256()
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
        return hasher.hexdigest().lower()

    @classmethod
    def calculate_sha256_bytes(cls, data: bytes) -> str:
        """
        Calculate SHA-256 hash of in-memory bytes.
        """
        return hashlib.sha256(data).hexdigest().lower()

    @classmethod
    def verify_sha256(cls, file_path: str, expected_hash: str) -> Tuple[bool, str]:
        """
        Verify the integrity of a stored evidence file by recalculating its SHA-256
        and comparing with the baseline original hash.
        Returns:
            (is_verified: bool, calculated_hash: str)
        """
        calculated_hash = cls.calculate_sha256_file(file_path)
        is_verified = (calculated_hash.lower() == expected_hash.strip().lower())
        return is_verified, calculated_hash
