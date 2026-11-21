# Frozen names in contracts/runtime.yaml; scripts and the grader use these exact outputs.
output "app_public_ip" {
  value = module.app.public_ip
}

output "app_instance_id" {
  value = module.app.instance_id
}

output "platform_instance_id" {
  value = module.platform.instance_id
}

output "llm_instance_id" {
  value = module.llm.instance_id
}

output "rds_endpoint" {
  value = module.rds.endpoint
}

output "artifact_bucket" {
  value = module.artifact_bucket.name
}

# Later stages use these private addresses for service-to-service traffic.
output "platform_private_ip" {
  value = module.platform.private_ip
}

output "llm_private_ip" {
  value = module.llm.private_ip
}
