# Private bucket for clothing photos. The API stores objects here through the
# instance role and answers /uploads/<file> with a short-lived presigned URL.
resource "aws_s3_bucket" "photos" {
  #checkov:skip=CKV_AWS_18:Server access logging is out of scope for a demo; CloudTrail records API activity
  #checkov:skip=CKV_AWS_144:Cross-region replication would double storage cost; versioning covers accidental deletes
  #checkov:skip=CKV_AWS_145:SSE-S3 (AES-256) instead of a customer-managed KMS key to avoid KMS cost
  #checkov:skip=CKV2_AWS_62:Nothing consumes object events
  bucket = "${local.name}-photos-${local.account_id}"
}

resource "aws_s3_bucket_public_access_block" "photos" {
  bucket = aws_s3_bucket.photos.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Disables ACLs entirely; access is controlled only by IAM and the bucket policy.
resource "aws_s3_bucket_ownership_controls" "photos" {
  bucket = aws_s3_bucket.photos.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "photos" {
  bucket = aws_s3_bucket.photos.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Versioning makes an accidental delete or overwrite recoverable.
resource "aws_s3_bucket_versioning" "photos" {
  bucket = aws_s3_bucket.photos.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "photos" {
  bucket = aws_s3_bucket.photos.id

  rule {
    id     = "expire-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.photos]
}

data "aws_iam_policy_document" "photos_bucket" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.photos.arn,
      "${aws_s3_bucket.photos.arn}/*",
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "photos" {
  bucket = aws_s3_bucket.photos.id
  policy = data.aws_iam_policy_document.photos_bucket.json

  depends_on = [aws_s3_bucket_public_access_block.photos]
}
