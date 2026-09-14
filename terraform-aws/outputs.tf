output "ecr_repository_url" {
  description = "Push the image here."
  value       = aws_ecr_repository.diarisk.repository_url
}

output "function_url" {
  description = "Public HTTPS endpoint of the API."
  value       = aws_lambda_function_url.diarisk.function_url
}

output "function_name" {
  description = "Lambda function name (used by the deploy workflow)."
  value       = aws_lambda_function.diarisk.function_name
}

output "github_actions_role_arn" {
  description = "Role ARN for the AWS_DEPLOY_ROLE_ARN secret."
  value       = aws_iam_role.github_actions.arn
}
