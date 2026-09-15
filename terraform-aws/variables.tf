variable "aws_region" {
  description = "AWS region for ECR and Lambda."
  type        = string
  default     = "eu-north-1"
}

variable "function_name" {
  description = "Lambda function name."
  type        = string
  default     = "diarisk-api"
}

variable "ecr_repository_name" {
  description = "ECR repository holding the DiaRisk image."
  type        = string
  default     = "diarisk"
}

variable "image_tag" {
  description = "Image tag used when the function is first created."
  type        = string
  default     = "latest"
}

variable "ecr_keep_images" {
  description = "How many images to keep in ECR (storage is only free up to 500 MB)."
  type        = number
  default     = 3
}

# 1024 MB is a good tradeoff: Lambda scales CPU with memory, so a bigger
# function finishes faster and often costs the same in GB-seconds.
variable "memory_size" {
  description = "Lambda memory in MB."
  type        = number
  default     = 1024
}

variable "timeout_seconds" {
  description = "Lambda timeout. Cold starts of this image take a few seconds."
  type        = number
  default     = 30
}

variable "reserved_concurrency" {
  description = "Maximum parallel executions. Keeps runaway traffic inside the free tier."
  type        = number
  default     = 5
}

variable "log_retention_days" {
  description = "CloudWatch log retention."
  type        = number
  default     = 7
}

variable "budget_alert_email" {
  description = "Email for the monthly budget alert. Empty disables the budget."
  type        = string
  default     = ""
}

variable "budget_limit_usd" {
  description = "Monthly budget that triggers the alert."
  type        = string
  default     = "1"
}

variable "github_repository" {
  description = "owner/repo allowed to push images and deploy via OIDC."
  type        = string
  default     = "wasimahmadpk/diarisk"
}

variable "enable_github_oidc" {
  description = "Wire GitHub Actions OIDC deploy. Off by default: the Free-plan SCP blocks iam:CreateOpenIDConnectProvider."
  type        = bool
  default     = false
}

variable "create_github_oidc_provider" {
  description = "Create the GitHub OIDC provider. Set to false if the account already has one."
  type        = bool
  default     = true
}
