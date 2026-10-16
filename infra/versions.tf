terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # State is local for now (terraform.tfstate, git-ignored).
  # Phase 8 moves it to S3: create the bucket with ./bootstrap, put its name
  # below, uncomment the block, then run:
  #   terraform init -migrate-state
  #
  # backend "s3" {
  #   bucket       = "wardrobe-ai-tfstate-<ACCOUNT_ID>"
  #   key          = "prod/terraform.tfstate"
  #   region       = "us-east-2"
  #   encrypt      = true
  #   use_lockfile = true # S3-native state locking (Terraform >= 1.10), no DynamoDB table
  # }
}
