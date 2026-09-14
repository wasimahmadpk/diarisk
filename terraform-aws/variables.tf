variable "aws_region" {
  description = "AWS region for ECR and App Runner."
  type        = string
  default     = "eu-central-1"
}

variable "service_name" {
  description = "App Runner service name."
  type        = string
  default     = "diarisk-api"
}

variable "ecr_repository_name" {
  description = "ECR repository holding the DiaRisk API image."
  type        = string
  default     = "diarisk"
}

variable "image_tag" {
  description = "Image tag App Runner runs."
  type        = string
  default     = "latest"
}

variable "container_port" {
  description = "Port uvicorn listens on inside the container."
  type        = number
  default     = 8000
}

# 1 vCPU / 2 GB is enough for a LightGBM pipeline; App Runner bills
# vCPU only while requests are being handled, memory continuously.
variable "cpu" {
  description = "vCPU units per instance (1024 = 1 vCPU)."
  type        = string
  default     = "1024"
}

variable "memory" {
  description = "Memory per instance in MB."
  type        = string
  default     = "2048"
}

variable "min_size" {
  description = "Minimum number of instances. App Runner cannot scale to zero."
  type        = number
  default     = 1
}

variable "max_size" {
  description = "Maximum number of instances."
  type        = number
  default     = 3
}

variable "max_concurrency" {
  description = "Requests per instance before scaling out."
  type        = number
  default     = 80
}

variable "github_repository" {
  description = "owner/repo allowed to push images and deploy via OIDC."
  type        = string
  default     = "wasimahmadpk/diarisk"
}

variable "create_github_oidc_provider" {
  description = "Create the GitHub OIDC provider. Set to false if the account already has one."
  type        = bool
  default     = true
}
