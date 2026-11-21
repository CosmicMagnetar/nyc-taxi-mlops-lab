# S0 runs in the Learner Lab's default VPC. Default subnets provide outbound access
# to GitHub/GHCR and SSM without a NAT gateway.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "all" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_subnets" "host_az" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "availability-zone"
    values = [var.availability_zone]
  }
}

module "app" {
  source             = "../modules/host"
  role               = "app"
  instance_type      = var.app_instance_type
  subnet_id          = sort(data.aws_subnets.host_az.ids)[0]
  security_group_ids = [aws_security_group.app.id]
}

module "platform" {
  source             = "../modules/host"
  role               = "platform"
  instance_type      = var.platform_instance_type
  subnet_id          = sort(data.aws_subnets.host_az.ids)[0]
  security_group_ids = [aws_security_group.platform.id]
}

module "llm" {
  source             = "../modules/host"
  role               = "llm"
  instance_type      = var.llm_instance_type
  subnet_id          = sort(data.aws_subnets.host_az.ids)[0]
  security_group_ids = [aws_security_group.llm.id]
}

module "rds" {
  source             = "../modules/rds"
  instance_class     = var.rds_instance_class
  subnet_ids         = sort(data.aws_subnets.all.ids)
  security_group_ids = [aws_security_group.rds.id]
}

module "artifact_bucket" {
  source = "../modules/bucket"
  name   = "lab-artifacts"
}

module "wiki_secret" {
  source      = "../modules/secret"
  name        = "lab/wiki"
  description = "Wiki credentials for the S6 support assistant"
}
