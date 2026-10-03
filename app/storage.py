"""Where uploaded photos end up.

Uploads are always written to the local upload directory first, because the
clothing analyzer reads the image from disk. With the S3 backend the file is
then moved into a private bucket and served through short-lived presigned URLs.
"""

import mimetypes
import os
from functools import lru_cache

from app.config import settings

KEY_PREFIX = "uploads/"


class LocalStorage:
    """Development and tests: the file stays on disk and StaticFiles serves it."""

    def persist(self, local_path: str) -> None:
        pass


class S3Storage:
    """Production: move the file into a private S3 bucket."""

    def __init__(self, bucket: str, client=None):
        if client is None:
            import boto3

            # No keys here: on EC2, boto3 picks up the instance role's temporary credentials.
            client = boto3.client("s3", region_name=settings.aws_region)
        self.bucket = bucket
        self.client = client

    def persist(self, local_path: str) -> None:
        key = KEY_PREFIX + os.path.basename(local_path)
        content_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
        self.client.upload_file(
            local_path, self.bucket, key, ExtraArgs={"ContentType": content_type}
        )
        # Only remove the local copy once the upload has succeeded.
        os.remove(local_path)

    def presigned_url(self, filename: str) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": KEY_PREFIX + filename},
            ExpiresIn=settings.presigned_url_ttl,
        )


@lru_cache
def get_storage():
    if settings.storage_backend == "s3":
        return S3Storage(bucket=settings.s3_bucket)
    return LocalStorage()