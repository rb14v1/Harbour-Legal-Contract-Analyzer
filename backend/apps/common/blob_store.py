"""
Blob storage abstraction.

Real path: Azure Blob Storage via `azure-storage-blob`, used when
AZURE_STORAGE_CONNECTION_STRING is configured.

Stub path: writes/reads files under MEDIA_ROOT/blob_stub/ on local disk.
Both paths expose the exact same function signatures so callers never need
to know which one is active.
"""
import os
import uuid

from django.conf import settings

STUB_SUBDIR = "blob_stub"


def _stub_root():
    root = os.path.join(settings.MEDIA_ROOT, STUB_SUBDIR)
    os.makedirs(root, exist_ok=True)
    return root


def _is_real():
    return bool(settings.AZURE_STORAGE_CONNECTION_STRING)


def _get_blob_service_client():
    from azure.storage.blob import BlobServiceClient

    return BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)


def upload_document(file, container: str, blob_name: str | None = None) -> str:
    """
    Upload `file` (a Django UploadedFile or file-like object opened in binary
    mode) into `container`. Returns a blob_path identifying the stored blob
    (real: "container/blob_name" path used to build/resolve the blob URL;
    stub: the same "container/blob_name" relative path on local disk).
    """
    if blob_name is None:
        suffix = ""
        name = getattr(file, "name", "")
        if "." in name:
            suffix = "." + name.rsplit(".", 1)[-1]
        blob_name = f"{uuid.uuid4().hex}{suffix}"

    if hasattr(file, "seek"):
        file.seek(0)
    data = file.read()
    if isinstance(data, str):
        data = data.encode("utf-8")

    if _is_real():
        client = _get_blob_service_client()
        try:
            client.create_container(container)
        except Exception:
            pass
        blob_client = client.get_blob_client(container=container, blob=blob_name)
        blob_client.upload_blob(data, overwrite=True)
        return f"{container}/{blob_name}"

    container_dir = os.path.join(_stub_root(), container)
    os.makedirs(container_dir, exist_ok=True)
    full_path = os.path.join(container_dir, blob_name)
    with open(full_path, "wb") as fh:
        fh.write(data)
    return f"{container}/{blob_name}"


def download_document(blob_path: str) -> bytes:
    """Return the raw bytes stored at `blob_path` ("container/blob_name")."""
    container, blob_name = blob_path.split("/", 1)

    if _is_real():
        client = _get_blob_service_client()
        blob_client = client.get_blob_client(container=container, blob=blob_name)
        return blob_client.download_blob().readall()

    full_path = os.path.join(_stub_root(), container, blob_name)
    with open(full_path, "rb") as fh:
        return fh.read()


def is_stub_mode() -> bool:
    return not _is_real()
