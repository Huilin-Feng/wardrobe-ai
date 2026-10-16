# Infrastructure

Terraform for the production environment of AI Wardrobe Assistant. Everything
in AWS is defined here except two things that must never pass through
Terraform state: the API keys (created by hand as SSM SecureString parameters)
and the TLS certificate (issued by Let's Encrypt on the server).

## What it creates

| File | Resources |
|---|---|
| `network.tf` | VPC, one public subnet, internet gateway, route table, a locked-down default security group, and the web security group (inbound 80/443 only; outbound 80/443 only; SSH closed unless `ssh_ingress_cidr` is set) |
| `compute.tf` | EC2 instance (Ubuntu 24.04, IMDSv2 only, encrypted gp3 root volume, standard CPU credits, auto recovery) and the Elastic IP plus its association |
| `imports.tf` | Adopts the existing hand-created Elastic IP so the public address does not change |
| `storage.tf` | Private photo bucket: public access blocked, ACLs disabled, SSE-S3, versioning, TLS-only bucket policy, lifecycle for old versions |
| `ecr.tf` | `wardrobe-ai-api` and `wardrobe-ai-web` repositories: immutable tags, scan on push, keep the last N images |
| `iam.tf` | Instance role scoped to one bucket, two repositories, one parameter path and one log group; a CI identity with the same narrow policy: by default a CI-only IAM user (this account's AWS-managed SCP blocks OIDC providers), or a GitHub OIDC role when `enable_github_oidc = true` |
| `deploy.tf` | SSM Command document that deploys one commit SHA; the only command the deploy role may send |
| `config.tf` | Non-secret runtime configuration in Parameter Store |
| `monitoring.tf` | CloudWatch log group, SNS alert topic, EC2 status-check alarm, Route 53 HTTPS health check and its alarm (us-east-1) |
| `budgets.tf` | Monthly cost budget with 50% / 80% actual and 100% forecast alerts, measured before credits |
| `cloudtrail.tf` | Multi-region CloudTrail trail with log file validation and its S3 bucket |
| `dns.tf` | A record for the domain, only when DNS is hosted in Route 53 |
| `bootstrap/` | S3 bucket for remote state, applied once on its own |

## How a deploy works

1. A push to `main` runs CI (tests, frontend build, image builds).
2. When CI passes, `.github/workflows/deploy.yml` authenticates as the CI
   identity (IAM user key from GitHub secrets, or OIDC when enabled), builds both images and pushes them to ECR
   tagged with the commit SHA.
3. It sends the `wardrobe-ai-deploy` SSM document to the instance. The
   instance checks out that commit and runs `deploy/deploy.sh`, which renders
   `.env` from Parameter Store, pulls the images and restarts the containers.
4. The script fails the deploy unless `/api/health` answers within a minute.

Rollback: run the Deploy workflow manually with an older commit SHA.

## Usage

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars   # set alert_email
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

Rollout switches in `terraform.tfvars`, flipped one phase at a time:

| Variable | Effect |
|---|---|
| `attach_eip` | Moves the Elastic IP from the old instance to the new one |
| `domain_name`, `route53_zone_id` | Publishes the domain to the server (and creates the DNS record if the zone is in Route 53) |
| `enable_health_check` | Creates the HTTPS health check and alarm; turn on after HTTPS works |

Secrets are created outside Terraform:

```bash
read -rs VALUE && aws ssm put-parameter --name /wardrobe-ai/prod/OPENAI_API_KEY \
  --type SecureString --value "$VALUE" --overwrite; unset VALUE
```

## Design notes

- **Single instance, single AZ.** No load balancer or NAT gateway, which keeps
  fixed monthly cost close to zero. The trade-off is listed in
  `docs/well-architected.md`.
- **The instance ignores AMI and user data changes** after creation, so a new
  Ubuntu release never silently replaces the server and its SQLite data.
- **Checkov skips are written next to the resource** with the reason, so every
  accepted risk is visible in code review.
