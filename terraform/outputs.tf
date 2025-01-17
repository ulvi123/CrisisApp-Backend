output "dynamodb_table_name" {
  description = "Name of the incidents table in DynamoDB"
  value       = aws_dynamodb_table.incidents.name
}

output "commands_lambda_name" {
  description = "Slack commands Lambda function name"
  value       = aws_lambda_function.slack_commands.function_name
}

output "interactions_lambda_name" {
  description = "Slack interactions Lambda function name"
  value       = aws_lambda_function.slack_interactions.function_name
}

output "apigateway_endpoint" {
  description = "HTTP API Gateway base endpoint"
  value       = "${aws_apigatewayv2_api.slack_api.api_endpoint}/${var.environment}"
}
