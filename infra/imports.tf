# Adopts the existing, hand-created Elastic IP so the public address (and every
# link that points at it) survives the move to the Terraform-managed stack.
#
# Replace the placeholder with the AllocationId from:
#   aws ec2 describe-addresses --query "Addresses[].[PublicIp,AllocationId]" --output table
#
# Importing only records the address in Terraform state. It stays attached to
# the old instance until attach_eip = true (Phase 5).
import {
  to = aws_eip.app
  id = "eipalloc-0a2d384cfa3be2a09"
}
