# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------
variable "aws_region" {
  description = "Region for all regional resources. The Route 53 health-check alarm is the one exception (us-east-1)."
  type        = string
  default     = "us-east-2"
}

variable "project" {
  description = "Name prefix for every resource."
  type        = string
  default     = "wardrobe-ai"
}

variable "environment" {
  description = "Environment name, used in tags, names and the Parameter Store path."
  type        = string
  default     = "prod"
}

variable "github_repo" {
  description = "Repository in owner/name form. The server clones it, and the deploy role trusts only its workflows."
  type        = string
  default     = "Huilin-Feng/wardrobe-ai"
}

variable "github_branch" {
  description = "Only workflows running on this branch may assume the deploy role."
  type        = string
  default     = "main"
}

variable "enable_github_oidc" {
  description = "CI authenticates with GitHub OIDC instead of an IAM user. Needs an account whose service control policies allow iam:CreateOpenIDConnectProvider."
  type        = bool
  default     = false
}

variable "alert_email" {
  description = "Receives budget, health-check and instance alerts. Each SNS topic sends a confirmation email first."
  type        = string

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "alert_email must be an email address."
  }
}

# ---------------------------------------------------------------------------
# Network and compute
# ---------------------------------------------------------------------------
variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "public_subnet_cidr" {
  type    = string
  default = "10.20.1.0/24"
}

variable "availability_zone" {
  type    = string
  default = "us-east-2a"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "root_volume_size_gb" {
  type    = number
  default = 20
}

variable "ssh_ingress_cidr" {
  description = "Optional single address allowed to SSH, e.g. \"203.0.113.7/32\". Empty keeps port 22 closed; use Session Manager instead."
  type        = string
  default     = ""
}

variable "ssh_key_name" {
  description = "Optional EC2 key pair name. Not needed when using Session Manager."
  type        = string
  default     = null
}

# ---------------------------------------------------------------------------
# Rollout switches (flip them phase by phase, see infra/README.md)
# ---------------------------------------------------------------------------
variable "attach_eip" {
  description = "Phase 5 (cutover): move the Elastic IP from the old instance to the new one."
  type        = bool
  default     = false
}

variable "domain_name" {
  description = "Phase 6: public hostname, e.g. \"wardrobe.example.com\". Empty means no domain yet."
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Optional Route 53 hosted zone ID for domain_name. Leave empty if DNS is managed at another registrar."
  type        = string
  default     = ""
}

variable "enable_health_check" {
  description = "Phase 6: create the Route 53 HTTPS health check and its alarm. Turn on only after HTTPS works."
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# Cost and retention
# ---------------------------------------------------------------------------
variable "monthly_budget_usd" {
  description = "Monthly cost budget in USD (gross, before credits)."
  type        = string
  default     = "20"
}

variable "ecr_keep_images" {
  description = "How many images to keep per ECR repository. Older ones expire."
  type        = number
  default     = 10
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention for container logs."
  type        = number
  default     = 14
}

variable "cloudtrail_log_retention_days" {
  description = "Days to keep CloudTrail log files in S3."
  type        = number
  default     = 90
}
