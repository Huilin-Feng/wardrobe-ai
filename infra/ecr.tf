locals {
  # One repository per Compose service: <project>-api, <project>-web.
  ecr_services = ["api", "web"]
}

resource "aws_ecr_repository" "app" {
  #checkov:skip=CKV_AWS_136:AES-256 (AWS-owned key) instead of a customer-managed KMS key to avoid KMS cost
  for_each = toset(local.ecr_services)

  name = "${local.name}-${each.key}"

  # Every image is tagged with its git commit SHA and can never be overwritten,
  # so a tag always means exactly one build.
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  for_each = aws_ecr_repository.app

  repository = each.value.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep only the most recent images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = var.ecr_keep_images
      }
      action = {
        type = "expire"
      }
    }]
  })
}
