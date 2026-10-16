# ===========================================================================
# EC2 instance role: what the server itself is allowed to do
# ===========================================================================
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "${local.name}-${var.environment}-ec2"
  description        = "Runtime role for the wardrobe-ai server"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_instance_profile" "app" {
  name = aws_iam_role.app.name
  role = aws_iam_role.app.name
}

# Lets the SSM agent register the instance, which enables Run Command (deploys)
# and Session Manager (shell access without SSH or an open port 22).
resource "aws_iam_role_policy_attachment" "app_ssm_core" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "app" {
  # Object-level access to exactly one bucket. No ListBucket, no other buckets.
  statement {
    sid       = "PhotoObjectsInOneBucket"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.photos.arn}/*"]
  }

  # ECR login tokens are account-wide; this action cannot be scoped to a repository.
  statement {
    sid       = "EcrLogin"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "PullAppImages"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [for repo in aws_ecr_repository.app : repo.arn]
  }

  # Only this environment's parameter path. SecureString values use the AWS
  # managed key aws/ssm, whose key policy already allows decryption through SSM.
  statement {
    sid     = "ReadRuntimeConfig"
    actions = ["ssm:GetParametersByPath", "ssm:GetParameters", "ssm:GetParameter"]
    resources = [
      "arn:aws:ssm:${var.aws_region}:${local.account_id}:parameter${local.ssm_prefix}",
      "arn:aws:ssm:${var.aws_region}:${local.account_id}:parameter${local.ssm_prefix}/*",
    ]
  }

  # Used by Docker's awslogs driver, which runs on the host with the instance role.
  statement {
    sid       = "ShipContainerLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams"]
    resources = ["${aws_cloudwatch_log_group.app.arn}:*"]
  }
}

resource "aws_iam_role_policy" "app" {
  name   = "${local.name}-runtime"
  role   = aws_iam_role.app.id
  policy = data.aws_iam_policy_document.app.json
}

# ===========================================================================
# CI identity for GitHub Actions
#
# Preferred: OIDC federation, so GitHub holds no AWS credentials at all.
# This account was created through AWS's new experience, whose AWS-managed
# service control policy denies iam:*Provider* (no OIDC providers) until
# advanced features are activated. So by default CI uses a dedicated IAM user
# instead. Both identities get exactly the same least-privilege policy, and
# enable_github_oidc = true switches to OIDC without other code changes.
# ===========================================================================
data "aws_iam_policy_document" "github_deploy" {
  statement {
    sid       = "EcrLogin"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "PushAppImages"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImages",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    resources = [for repo in aws_ecr_repository.app : repo.arn]
  }

  # The pipeline can run exactly one thing on exactly one instance: the deploy
  # document, which only accepts a 40-character commit SHA. It cannot run
  # arbitrary shell commands (AWS-RunShellScript is not allowed).
  statement {
    sid     = "RunDeployDocument"
    actions = ["ssm:SendCommand"]
    resources = [
      aws_instance.app.arn,
      aws_ssm_document.deploy.arn,
    ]
  }

  # Command invocations do not support resource-level permissions.
  statement {
    sid       = "ReadDeployResult"
    actions   = ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"]
    resources = ["*"]
  }
}

# --- Option 1 (default): dedicated IAM user --------------------------------
# Its access key is created by hand with the AWS CLI and stored only in GitHub
# Actions secrets, so the secret never appears in Terraform state.
resource "aws_iam_user" "github_deploy" {
  #checkov:skip=CKV_AWS_273:SSO and OIDC federation are blocked by this account's service control policy; this user is CI-only and least-privilege
  count = var.enable_github_oidc ? 0 : 1

  name = "${local.name}-github-deploy"
}

resource "aws_iam_user_policy" "github_deploy" {
  #checkov:skip=CKV_AWS_40:IAM groups are blocked by this account's service control policy (iam:CreateGroup is denied)
  count = var.enable_github_oidc ? 0 : 1

  name   = "${local.name}-deploy"
  user   = aws_iam_user.github_deploy[0].name
  policy = data.aws_iam_policy_document.github_deploy.json
}

# --- Option 2: OIDC federation (enable_github_oidc = true) ------------------
resource "aws_iam_openid_connect_provider" "github" {
  count = var.enable_github_oidc ? 1 : 0

  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]

  # AWS verifies GitHub's OIDC endpoint against its own trusted CAs. These
  # well-known thumbprints are kept only for tooling that still expects them.
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]
}

data "aws_iam_policy_document" "github_assume" {
  count = var.enable_github_oidc ? 1 : 0

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github[0].arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Only workflows on one branch of one repository. Forks, pull requests and
    # other branches get a different "sub" claim and are rejected.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:ref:refs/heads/${var.github_branch}"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  count = var.enable_github_oidc ? 1 : 0

  name                 = "${local.name}-github-deploy"
  description          = "Assumed by GitHub Actions to push images and trigger deploys"
  assume_role_policy   = data.aws_iam_policy_document.github_assume[0].json
  max_session_duration = 3600
}

resource "aws_iam_role_policy" "github_deploy" {
  count = var.enable_github_oidc ? 1 : 0

  name   = "${local.name}-deploy"
  role   = aws_iam_role.github_deploy[0].id
  policy = data.aws_iam_policy_document.github_deploy.json
}
