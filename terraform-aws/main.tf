# DiaRisk on AWS App Runner:
# ECR holds the image, App Runner pulls it and serves it behind a managed
# HTTPS endpoint with autoscaling. No VPC, load balancer or cluster needed.

resource "aws_ecr_repository" "diarisk" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "diarisk" {
  repository = aws_ecr_repository.diarisk.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the 10 most recent images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThanNumber"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

# App Runner assumes this role to pull from ECR.
data "aws_iam_policy_document" "apprunner_ecr_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["build.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apprunner_ecr_access" {
  name               = "${var.service_name}-ecr-access"
  assume_role_policy = data.aws_iam_policy_document.apprunner_ecr_assume.json
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access" {
  role       = aws_iam_role.apprunner_ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_apprunner_auto_scaling_configuration_version" "diarisk" {
  auto_scaling_configuration_name = var.service_name
  min_size                        = var.min_size
  max_size                        = var.max_size
  max_concurrency                 = var.max_concurrency

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_apprunner_service" "diarisk" {
  service_name = var.service_name

  source_configuration {
    # New pushes to the tracked tag redeploy the service automatically.
    auto_deployments_enabled = true

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }

    image_repository {
      image_identifier      = "${aws_ecr_repository.diarisk.repository_url}:${var.image_tag}"
      image_repository_type = "ECR"

      image_configuration {
        port = tostring(var.container_port)

        runtime_environment_variables = {
          PYTHONUNBUFFERED = "1"
        }
      }
    }
  }

  instance_configuration {
    cpu    = var.cpu
    memory = var.memory
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.diarisk.arn

  depends_on = [aws_iam_role_policy_attachment.apprunner_ecr_access]
}
