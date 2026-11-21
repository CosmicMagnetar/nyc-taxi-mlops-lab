# S1: the Redshift warehouse. A single ra3.large node, in the same AZ as the hosts.
# Clients use the Data API, so the cluster has no ingress and its admin password is stored nowhere.
module "warehouse" {
  source            = "../modules/redshift"
  subnet_ids        = sort(data.aws_subnets.all.ids)
  availability_zone = var.availability_zone
}

# Names listed under terraform_outputs in contracts/platform.yaml.
output "redshift_cluster_id" {
  value = module.warehouse.cluster_id
}

output "redshift_database" {
  value = module.warehouse.database
}
