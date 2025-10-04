variable "project_name" {
  description = "Project name"
  type        = string
  default     = "emg-classifier"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-north-1"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones for subnets"
  type        = list(string)
  default     = ["eu-north-1a", "eu-north-1b"]
}

variable "api_image_url" {
  description = "Docker image URL for API"
  type        = string
}

variable "frontend_image_url" {
  description = "Docker image URL for Frontend"
  type        = string
  default     = ""
}