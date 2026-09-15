"""Google Cloud Storage client for Document uploads (PRD: file upload
sources feed Datasets/Documents). Demo-level: no signed URLs, no
resumable upload for large files, no lifecycle/retention policy --
just put/get bytes against a bucket.

Falls back to local-disk storage under /tmp if GCS_BUCKET isn't
configured, so the rest of the Documents feature is exercisable without
real GCP credentials in a local/dev environment. This fallback is a
deliberate convenience for this demo pass, not a production storage
backend -- flagged, not hidden.
"""

from __future__ import annotations

import os
import uuid

from libs.gcp.config import GCS_BUCKET

_LOCAL_FALLBACK_DIR = "/tmp/autonomousiq-documents"


def _using_gcs() -> bool:
    return bool(GCS_BUCKET)


def upload_bytes(content: bytes, *, filename: str, tenant_id: str) -> str:
    """Stores `content` and returns a storage_pointer string (gs:// URI
    or a local path) suitable for Document.storage_pointer."""
    object_key = f"{tenant_id}/{uuid.uuid4()}-{filename}"

    if _using_gcs():
        from google.cloud import storage  # local import: optional dependency

        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(object_key)
        blob.upload_from_string(content)
        return f"gs://{GCS_BUCKET}/{object_key}"

    os.makedirs(os.path.join(_LOCAL_FALLBACK_DIR, tenant_id), exist_ok=True)
    local_path = os.path.join(_LOCAL_FALLBACK_DIR, object_key)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "wb") as f:
        f.write(content)
    return local_path


def download_bytes(storage_pointer: str) -> bytes:
    if storage_pointer.startswith("gs://"):
        from google.cloud import storage

        _, _, rest = storage_pointer.partition("gs://")
        bucket_name, _, object_key = rest.partition("/")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_key)
        return blob.download_as_bytes()

    with open(storage_pointer, "rb") as f:
        return f.read()
