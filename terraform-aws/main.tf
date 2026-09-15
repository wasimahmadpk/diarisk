# DiaRisk on AWS Lambda:
# ECR holds the container image, Lambda runs it, a Function URL exposes it
# over HTTPS. Lambda scales to zero, so an idle service costs nothing and
# normal usage stays inside the always-free tier (1M requests + 400k GB-s
# per month).

resource "aws_ecr_repository" "diarisk" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# ECR storage is the one thing that is not free forever (500 MB for the first
# 12 months), so keep only a few images around.
resource "aws_ecr_lifecycle_policy" "diarisk" {
  repository = aws_ecr_repository.diarisk.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the ${var.ecr_keep_images} most recent images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = var.ecr_keep_images
      }
      action = { type = "expire" }
    }]
  })
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Created explicitly so logs expire instead of accumulating forever.
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "diarisk" {
  function_name = var.function_name
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.diarisk.repository_url}:${var.image_tag}"
  architectures = ["x86_64"]

  memory_size = var.memory_size
  timeout     = var.timeout_seconds

  # Hard cap so a runaway loop or traffic spike cannot blow past the free tier.
  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DIARISK_MODEL_PATH = "/var/task/models/diarisk_lightgbm.joblib"
    }
  }

  lifecycle {
    # CI deploys new images; Terraform should not roll them back.
    ignore_changes = [image_uri]
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_logs,
    aws_cloudwatch_log_group.lambda,
  ]
}

resource "aws_lambda_function_url" "diarisk" {
  function_name      = aws_lambda_function.diarisk.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["*"]
    allow_headers = ["*"]
  }
}

# Function URLs stay Forbidden on the AWS (new) Free plan even with AuthType NONE.
# HTTP API is allowed in the home Region and gives a public HTTPS URL.
resource "aws_apigatewayv2_api" "http" {
  name          = "${var.function_name}-http"
  protocol_type = "HTTP"
  description   = "Public HTTP front door for DiaRisk"
  target        = aws_lambda_function.diarisk.arn
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.diarisk.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

# Optional safety net: mail as soon as the account is forecast to cost money.
resource "aws_budgets_budget" "diarisk" {
  count = var.budget_alert_email == "" ? 0 : 1

  name         = "${var.function_name}-monthly"
  budget_type  = "COST"
  limit_amount = var.budget_limit_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_alert_email]
  }
}
