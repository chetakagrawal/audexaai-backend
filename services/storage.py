"""Storage service for evidence files (local disk for dev MVP)."""

import hashlib
import os
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

import config


async def save_upload(
    file: UploadFile,
    storage_key: str,
) -> tuple[int, str]:
    """
    Save uploaded file to local disk and compute SHA256 hash.
    
    Args:
        file: FastAPI UploadFile object
        storage_key: Storage path/key (e.g., "{tenant_id}/{project_id}/{artifact_id}/{file_id}-{filename}")
    
    Returns:
        Tuple of (bytes_written, sha256_hex)
    
    Raises:
        OSError: If directory creation or file write fails
    """
    storage_dir = Path(config.settings.EVIDENCE_STORAGE_DIR)
    full_path = storage_dir / storage_key
    
    # Create parent directories if they don't exist
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read file content and compute hash
    content = await file.read()
    sha256_hash = hashlib.sha256(content).hexdigest()
    
    # Write to disk
    with open(full_path, "wb") as f:
        bytes_written = f.write(content)
    
    return bytes_written, sha256_hash


async def delete_file(storage_key: str) -> None:
    """
    Delete a file from storage.
    
    Args:
        storage_key: Storage path/key to delete
    
    Raises:
        OSError: If file deletion fails
    """
    storage_dir = Path(config.settings.EVIDENCE_STORAGE_DIR)
    full_path = storage_dir / storage_key
    
    if full_path.exists():
        full_path.unlink()
        # Optionally remove empty parent directories (not implemented for MVP)


def generate_storage_key(
    tenant_id: UUID,
    project_id: UUID,
    artifact_id: UUID,
    file_id: UUID,
    filename: str,
) -> str:
    """
    Generate a storage key for a file.
    
    Args:
        tenant_id: Tenant ID
        project_id: Project ID
        artifact_id: Artifact ID
        file_id: File ID
        filename: Original filename (will be sanitized)
    
    Returns:
        Storage key path string
    """
    # Sanitize filename (remove path separators and other problematic chars)
    sanitized = filename.replace("/", "_").replace("\\", "_").replace("..", "_")
    
    return f"{tenant_id}/{project_id}/{artifact_id}/{file_id}-{sanitized}"

