from app.storage import S3Storage


class FakeS3:
    """Records calls instead of talking to AWS."""

    def __init__(self):
        self.uploads = []

    def upload_file(self, filename, bucket, key, ExtraArgs=None):
        self.uploads.append((filename, bucket, key, ExtraArgs))

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        return f"https://example.test/{Params['Bucket']}/{Params['Key']}?expires={ExpiresIn}"


def test_persist_uploads_to_bucket_then_removes_local_copy(tmp_path):
    photo = tmp_path / "abc.jpg"
    photo.write_bytes(b"fake image")
    fake = FakeS3()

    S3Storage(bucket="test-bucket", client=fake).persist(str(photo))

    _, bucket, key, extra = fake.uploads[0]
    assert (bucket, key) == ("test-bucket", "uploads/abc.jpg")
    assert extra == {"ContentType": "image/jpeg"}
    assert not photo.exists()


def test_presigned_url_points_at_uploads_prefix():
    url = S3Storage(bucket="test-bucket", client=FakeS3()).presigned_url("abc.jpg")
    assert url.startswith("https://example.test/test-bucket/uploads/abc.jpg")