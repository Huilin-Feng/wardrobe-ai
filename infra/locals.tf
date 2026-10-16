data "aws_caller_identity" "current" {}

locals {
  name       = var.project
  account_id = data.aws_caller_identity.current.account_id

  # Applied to every resource through the providers' default_tags.
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
    Repository  = var.github_repo
  }

  # Parameter Store path the server reads all of its runtime configuration from.
  ssm_prefix = "/${var.project}/${var.environment}"

  ecr_registry = "${local.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"

  health_check_enabled = var.enable_health_check && var.domain_name != ""
}
