from pathlib import Path

from django.conf import settings
from supabase import create_client

# =========================================================
# SUPABASE CLIENT
# =========================================================

supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SECRET_KEY,
)


BUCKET_NAME = settings.SUPABASE_STORAGE_BUCKET


# =========================================================
# UPLOAD FILE
# =========================================================


def upload_file(
    local_file_path,
    storage_path,
    content_type=None,
):
    """
    Upload a local file to Supabase Storage.

    Returns:
        Storage path
    """

    local_file_path = Path(local_file_path)

    with open(local_file_path, "rb") as file:

        options = {
            "upsert": "true",
        }

        if content_type:
            options["content-type"] = content_type

        supabase.storage.from_(BUCKET_NAME).upload(
            storage_path,
            file,
            options,  # type: ignore
        )

    return storage_path


def get_file_url(
    storage_path,
    expires_in=3600,
):
    """
    Generate a signed URL for a stored file.
    """

    result = supabase.storage.from_(BUCKET_NAME).create_signed_url(
        storage_path,
        expires_in,
    )

    return result["signedURL"]
