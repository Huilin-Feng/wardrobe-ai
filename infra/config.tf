# Non-secret runtime configuration, written to Parameter Store so the server
# has a single source of configuration. deploy/deploy.sh reads the whole
# ${local.ssm_prefix}/ path and renders it into .env.
#
# Secrets (OPENAI_API_KEY, WEATHER_API_KEY) live under the same path as
# SecureString parameters but are created by hand with the AWS CLI. Passing
# them through Terraform would store them in plain text in the state file.
locals {
  runtime_config = merge(
    {
      STORAGE_BACKEND = "s3"
      S3_BUCKET       = aws_s3_bucket.photos.bucket
      AWS_REGION      = var.aws_region
      ECR_REGISTRY    = local.ecr_registry
      LOG_GROUP       = aws_cloudwatch_log_group.app.name
    },
    var.domain_name == "" ? {} : { DOMAIN_NAME = var.domain_name },
  )
}

resource "aws_ssm_parameter" "config" {
  #checkov:skip=CKV2_AWS_34:Non-secret configuration; secrets are separate SecureString parameters
  for_each = local.runtime_config

  name  = "${local.ssm_prefix}/${each.key}"
  type  = "String"
  value = each.value
}
