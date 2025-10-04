output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = module.ecs.alb_dns_name
}

output "api_url" {
  description = "API URL"
  value       = "http://${module.ecs.alb_dns_name}"
}

output "health_check_url" {
  description = "Health check URL"
  value       = "http://${module.ecs.alb_dns_name}/health"
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.ecs_cluster_name
}

output "api_service_name" {
  description = "API service name"
  value       = module.ecs.api_service_name
}