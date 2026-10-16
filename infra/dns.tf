# Only when the domain's DNS is hosted in Route 53. With another registrar,
# create the same A record there by hand (name -> Elastic IP).
resource "aws_route53_record" "app" {
  count = var.domain_name != "" && var.route53_zone_id != "" ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 300
  records = [aws_eip.app.public_ip]
}
