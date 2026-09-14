output "ecr_repository_url" {
  description = "Push the image here."
  value       = aws_ecr_repository.diarisk.repository_url
}

output "service_url" {
  description = "Public HTTPS endpoint of the API."
  value       = "https://${aws_apprunner_service.diarisk.service_url}"
}

output "service_arn" {
  description = "App Runner service ARN (used by the deploy workflow)."
  value       = aws_apprunner_service.diarisk.arn
}

output "github_actions_role_arn" {
  description = "Role ARN for the AWS_DEPLOY_ROLE_ARN secret."
  value       = aws_iam_role.github_actions.arn
}
