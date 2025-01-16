variable "aws_region" {
  type        = string
  default     = "eu-west-1"
}

variable "aws_profile" {
  type        = string
  default     = "gsg-intools-prod"
}

variable "environment" {
  type        = string
  default     = "prod"
}

variable "prefix" {
  type        = string
  description = "Prefix for resource names"
  default     = "crisisapp"
}

# Secrets
variable "slack_signing_secret" {
  type        = string
  description = "Slack signing secret for request verification"
  sensitive   = true
}

variable "slack_verification_token" {
  type        = string
  description = "Slack verification token for slash commands"
  sensitive   = true
}

variable "slack_bot_token" {
  type        = string
  description = "Slack Bot User OAuth token"
  sensitive   = true
}

