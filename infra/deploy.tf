# Custom SSM Command document: the only command the CI role may send.
# It checks out one commit of the public repository and runs that commit's
# deploy/deploy.sh, so what runs on the server is always in git history.
resource "aws_ssm_document" "deploy" {
  name          = "${local.name}-deploy"
  document_type = "Command"

  content = jsonencode({
    schemaVersion = "2.2"
    description   = "Deploy one commit of ${var.project} on this host"
    parameters = {
      CommitSha = {
        type           = "String"
        description    = "Full 40-character git commit SHA, which is also the image tag"
        allowedPattern = "^[0-9a-f]{40}$"
      }
    }
    mainSteps = [{
      action = "aws:runShellScript"
      name   = "deploy"
      inputs = {
        timeoutSeconds = "900"
        runCommand = [
          "cd /opt/${var.project} && git fetch --quiet origin && git checkout --quiet --force {{ CommitSha }} && bash deploy/deploy.sh {{ CommitSha }}",
        ]
      }
    }]
  })
}
