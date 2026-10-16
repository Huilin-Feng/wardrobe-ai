resource "aws_vpc" "main" {
  #checkov:skip=CKV2_AWS_11:Flow logs deferred to keep the demo near zero cost; tracked in docs/well-architected.md
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${local.name}-vpc"
  }
}

# Strip every rule from the VPC's default security group so nothing can end up
# in it by accident. All real traffic rules live in aws_security_group.web.
resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${local.name}-default-locked"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${local.name}-igw"
  }
}

resource "aws_subnet" "public" {
  #checkov:skip=CKV_AWS_130:One public web server by design; no load balancer or NAT gateway keeps fixed cost at zero
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = true

  tags = {
    Name = "${local.name}-public-${var.availability_zone}"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${local.name}-public"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ---------------------------------------------------------------------------
# Security group for the web server
# ---------------------------------------------------------------------------
resource "aws_security_group" "web" {
  name        = "${local.name}-web"
  description = "Public web traffic for the wardrobe-ai server"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${local.name}-web"
  }
}

resource "aws_vpc_security_group_ingress_rule" "http" {
  #checkov:skip=CKV_AWS_260:Port 80 must be public for the HTTP-to-HTTPS redirect and the Let's Encrypt HTTP-01 challenge
  security_group_id = aws_security_group.web.id
  description       = "HTTP from anywhere (redirects to HTTPS)"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = aws_security_group.web.id
  description       = "HTTPS from anywhere"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

# Port 22 stays closed unless ssh_ingress_cidr is set. Session Manager replaces SSH.
resource "aws_vpc_security_group_ingress_rule" "ssh" {
  count = var.ssh_ingress_cidr == "" ? 0 : 1

  security_group_id = aws_security_group.web.id
  description       = "SSH from a single trusted address"
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_ipv4         = var.ssh_ingress_cidr
}

# Outbound traffic is limited to web ports, which covers everything the server
# calls: OpenAI, OpenWeatherMap, GitHub, ECR, S3, SSM, CloudWatch Logs and
# Let's Encrypt on 443, and the Ubuntu apt mirrors on 80 (packages are
# signature-checked). DNS, NTP and the instance metadata service use addresses
# that security groups do not filter.
resource "aws_vpc_security_group_egress_rule" "https" {
  security_group_id = aws_security_group.web.id
  description       = "HTTPS to the internet and AWS APIs"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "http" {
  security_group_id = aws_security_group.web.id
  description       = "HTTP to the Ubuntu package mirrors"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}
