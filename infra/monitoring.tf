# ---------------------------------------------------------------------------
# Container logs
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "app" {
  #checkov:skip=CKV_AWS_158:Encrypted with the CloudWatch Logs service key; a customer-managed KMS key adds cost
  #checkov:skip=CKV_AWS_338:Short retention on purpose for a demo; CloudTrail keeps the audit trail
  name              = "/${local.name}/${var.environment}"
  retention_in_days = var.log_retention_days
}

# ---------------------------------------------------------------------------
# Alert topic in the main region
# ---------------------------------------------------------------------------
# Not encrypted with the AWS managed SNS key on purpose: CloudWatch alarms
# cannot publish to a topic that uses aws/sns, and a customer-managed key adds cost.
resource "aws_sns_topic" "alerts" {
  #checkov:skip=CKV_AWS_26:CloudWatch alarms cannot publish to topics encrypted with the AWS managed key
  name = "${local.name}-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Fires when either the EC2 system check or the instance check fails.
# Host failures are already handled by auto recovery; this makes sure a human hears about it.
resource "aws_cloudwatch_metric_alarm" "instance_status" {
  alarm_name          = "${local.name}-instance-status-check-failed"
  alarm_description   = "EC2 status checks are failing on the wardrobe-ai server."
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 3
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"

  dimensions = {
    InstanceId = aws_instance.app.id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# ---------------------------------------------------------------------------
# Public HTTPS health check (Phase 6). Route 53 probes /api/health from
# several locations; the alarm and its topic must be in us-east-1.
# ---------------------------------------------------------------------------
resource "aws_route53_health_check" "app" {
  count = local.health_check_enabled ? 1 : 0

  fqdn              = var.domain_name
  type              = "HTTPS"
  port              = 443
  resource_path     = "/api/health"
  request_interval  = 30
  failure_threshold = 3

  tags = {
    Name = "${local.name}-https"
  }
}

resource "aws_sns_topic" "alerts_us_east_1" {
  #checkov:skip=CKV_AWS_26:CloudWatch alarms cannot publish to topics encrypted with the AWS managed key
  count    = local.health_check_enabled ? 1 : 0
  provider = aws.us_east_1

  name = "${local.name}-alerts"
}

resource "aws_sns_topic_subscription" "alerts_us_east_1_email" {
  count    = local.health_check_enabled ? 1 : 0
  provider = aws.us_east_1

  topic_arn = aws_sns_topic.alerts_us_east_1[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "health_check" {
  count    = local.health_check_enabled ? 1 : 0
  provider = aws.us_east_1

  alarm_name          = "${local.name}-health-check-failed"
  alarm_description   = "https://${var.domain_name}/api/health is failing from Route 53 health checkers."
  namespace           = "AWS/Route53"
  metric_name         = "HealthCheckStatus"
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 3
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  # No data means the check itself is broken, which is also worth an email.
  treat_missing_data = "breaching"

  dimensions = {
    HealthCheckId = aws_route53_health_check.app[0].id
  }

  alarm_actions = [aws_sns_topic.alerts_us_east_1[0].arn]
  ok_actions    = [aws_sns_topic.alerts_us_east_1[0].arn]
}
