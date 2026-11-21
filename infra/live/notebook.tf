# S2: the SageMaker notebook, in the hosts' subnet. It clones the public repo set in github_repo
# (terraform.tfvars) and reaches MLflow on the platform host (port 5000, runtime.yaml).
module "notebook" {
  source    = "../modules/notebook"
  subnet_id = sort(data.aws_subnets.host_az.ids)[0]
  repo_url  = "https://github.com/${var.github_repo}.git"
  env = {
    MLFLOW_TRACKING_URI = "http://${module.platform.private_ip}:5000"
    REDSHIFT_CLUSTER_ID = module.warehouse.cluster_id
    REDSHIFT_DATABASE   = module.warehouse.database
    REDSHIFT_DB_USER    = module.warehouse.admin_user
  }
}

resource "aws_vpc_security_group_ingress_rule" "notebook_to_mlflow" {
  security_group_id            = aws_security_group.platform.id
  referenced_security_group_id = module.notebook.security_group_id
  description                  = "notebook to mlflow"
  ip_protocol                  = "tcp"
  from_port                    = 5000
  to_port                      = 5000
}

output "notebook_name" {
  value = module.notebook.name
}
