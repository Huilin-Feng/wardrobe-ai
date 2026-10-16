# Latest Ubuntu 24.04 LTS (x86_64) AMI published by Canonical.
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "app" {
  #checkov:skip=CKV_AWS_88:Single public web server by design; inbound is limited to 80/443 by the security group
  #checkov:skip=CKV_AWS_126:Detailed monitoring is billed; free 5-minute metrics and 1-minute status checks are enough here
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name
  key_name               = var.ssh_key_name
  ebs_optimized          = true
  monitoring             = false

  # "standard" throttles the CPU when burst credits run out. The default for
  # t3, "unlimited", keeps running at full speed and bills for the extra CPU.
  credit_specification {
    cpu_credits = "standard"
  }

  # IMDSv2 only. The hop limit is 2 because boto3 runs inside a Docker
  # container, one network hop past the host; with the default limit of 1 the
  # container could not fetch the instance role credentials.
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size_gb
    encrypted             = true
    delete_on_termination = true
  }

  # EC2 moves the instance to healthy hardware after a host failure.
  maintenance_options {
    auto_recovery = "default"
  }

  user_data = templatefile("${path.module}/templates/user_data.sh.tftpl", {
    aws_region  = var.aws_region
    ssm_prefix  = local.ssm_prefix
    github_repo = var.github_repo
  })

  tags = {
    Name = "${local.name}-${var.environment}"
  }

  lifecycle {
    # A newer Ubuntu AMI or an edited bootstrap script would otherwise force a
    # replacement, and the SQLite database lives on this disk. Roll those out on purpose.
    ignore_changes = [ami, user_data]
  }

  # First boot installs packages, so the subnet must already route to the internet.
  depends_on = [aws_route_table_association.public]
}

# ---------------------------------------------------------------------------
# Elastic IP (adopted from the old stack through imports.tf)
# ---------------------------------------------------------------------------
resource "aws_eip" "app" {
  domain = "vpc"

  tags = {
    Name = "${local.name}-eip"
  }

  # Releasing this address would break the public link; refuse to destroy it.
  lifecycle {
    prevent_destroy = true
  }
}

# Phase 5 (cutover): attach_eip = true moves the address to the new instance.
resource "aws_eip_association" "app" {
  count = var.attach_eip ? 1 : 0

  allocation_id       = aws_eip.app.id
  instance_id         = aws_instance.app.id
  allow_reassociation = true
}
