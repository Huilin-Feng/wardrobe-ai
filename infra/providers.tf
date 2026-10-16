provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# Route 53 publishes health-check metrics only in us-east-1, so the alarm that
# watches the health check (and the SNS topic it notifies) must live there.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = local.common_tags
  }
}
