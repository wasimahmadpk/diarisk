output "ecr_repository_url" {
  description = "Push the image here."
  value       = aws_ecr_repository.diarisk.repository_url
}

output "function_url" {
  description = "Lambda Function URL (may be Forbidden on the Free plan)."
  value       = aws_lambda_function_url.diarisk.function_url
}

output "api_url" {
  description = "Public HTTPS endpoint via API Gateway."
  value       = aws_apigatewayv2_api.http.api_endpoint
}

output "function_name" {
  description = "Lambda function name (used by the deploy workflow)."
  value       = aws_lambda_function.diarisk.function_name
}

output "github_actions_role_arn" {
  description = "Role ARN for the AWS_DEPLOY_ROLE_ARN secret. Null until enable_github_oidc is true."
  value       = var.enable_github_oidc ? aws_iam_role.github_actions[0].arn : null
}
