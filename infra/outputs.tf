output "instance_id" {
  description = "New EC2 instance."
  value       = aws_instance.app.id
}

output "instance_temporary_ip" {
  description = "Auto-assigned public IP, used for testing until the Elastic IP moves over in Phase 5."
  value       = aws_instance.app.public_ip
}

output "elastic_ip" {
  description = "The adopted Elastic IP."
  value       = aws_eip.app.public_ip
}

output "photos_bucket" {
  description = "Private bucket for clothing photos."
  value       = aws_s3_bucket.photos.bucket
}

output "ecr_repositories" {
  description = "Image repository URLs."
  value       = { for service, repo in aws_ecr_repository.app : service => repo.repository_url }
}

output "log_group" {
  description = "CloudWatch Logs group for container logs."
  value       = aws_cloudwatch_log_group.app.name
}

output "ssm_parameter_prefix" {
  description = "Parameter Store path for runtime configuration and secrets."
  value       = local.ssm_prefix
}

output "github_actions_variables" {
  description = "Repository variables (Settings > Secrets and variables > Actions > Variables). AWS_DEPLOY_ROLE_ARN is empty unless OIDC is enabled."
  value = {
    AWS_DEPLOY_ROLE_ARN = try(aws_iam_role.github_deploy[0].arn, "")
    EC2_INSTANCE_ID     = aws_instance.app.id
  }
}

output "github_deploy_user" {
  description = "IAM user whose access key goes into GitHub secrets (empty when OIDC is enabled)."
  value       = try(aws_iam_user.github_deploy[0].name, "")
}
