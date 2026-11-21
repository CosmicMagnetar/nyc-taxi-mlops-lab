# S0: app ingress is the student's CIDR choice. Internal ports follow
# contracts/runtime.yaml. SSM needs outbound access, never SSH ingress.
resource "aws_security_group" "app" {
  name_prefix = "lab-app-"
  description = "Ride app and Traefik host"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_security_group" "platform" {
  name_prefix = "lab-platform-"
  description = "Dagster and MLflow host"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_security_group" "llm" {
  name_prefix = "lab-llm-"
  description = "Chat and embedding model host"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_security_group" "rds" {
  name_prefix = "lab-rds-"
  description = "Private Postgres database"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_egress_rule" "host_outbound" {
  for_each = {
    app      = aws_security_group.app.id
    platform = aws_security_group.platform.id
    llm      = aws_security_group.llm.id
  }
  security_group_id = each.value
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "public_app" {
  for_each          = toset(var.ingress_cidrs)
  security_group_id = aws_security_group.app.id
  description       = "HTTP rider API"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = each.value
}

locals {
  internal_ingress = {
    app_to_mlflow = {
      destination = aws_security_group.platform.id
      source      = aws_security_group.app.id
      port        = 5000
    }
    app_to_llm_chat = {
      destination = aws_security_group.llm.id
      source      = aws_security_group.app.id
      port        = 8080
    }
    app_to_llm_embed = {
      destination = aws_security_group.llm.id
      source      = aws_security_group.app.id
      port        = 8081
    }
    platform_to_llm_chat = {
      destination = aws_security_group.llm.id
      source      = aws_security_group.platform.id
      port        = 8080
    }
    platform_to_llm_embed = {
      destination = aws_security_group.llm.id
      source      = aws_security_group.platform.id
      port        = 8081
    }
    app_to_rds = {
      destination = aws_security_group.rds.id
      source      = aws_security_group.app.id
      port        = 5432
    }
    platform_to_rds = {
      destination = aws_security_group.rds.id
      source      = aws_security_group.platform.id
      port        = 5432
    }
  }
}

resource "aws_vpc_security_group_ingress_rule" "internal" {
  for_each                     = local.internal_ingress
  security_group_id            = each.value.destination
  referenced_security_group_id = each.value.source
  description                  = replace(each.key, "_", " ")
  ip_protocol                  = "tcp"
  from_port                    = each.value.port
  to_port                      = each.value.port
}
