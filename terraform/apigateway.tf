# Create an API Gateway
resource "aws_apigatewayv2_api" "slack_api" {
  name          = "${var.prefix}-slack-api-${var.environment}"
  protocol_type = "HTTP"
}

# Integration for commands Lambda
resource "aws_apigatewayv2_integration" "commands_integration" {
  api_id              = aws_apigatewayv2_api.slack_api.id
  integration_type    = "AWS_PROXY"
  integration_uri     = aws_lambda_function.slack_commands.arn
  integration_method  = "POST"
  payload_format_version = "2.0"
}

# Integration for interactions Lambda
resource "aws_apigatewayv2_integration" "interactions_integration" {
  api_id              = aws_apigatewayv2_api.slack_api.id
  integration_type    = "AWS_PROXY"
  integration_uri     = aws_lambda_function.slack_interactions.arn
  integration_method  = "POST"
  payload_format_version = "2.0"
}

# Create routes:
resource "aws_apigatewayv2_route" "commands_route" {
  api_id    = aws_apigatewayv2_api.slack_api.id
  route_key = "POST /commands"
  target    = "integrations/${aws_apigatewayv2_integration.commands_integration.id}"
}

resource "aws_apigatewayv2_route" "interactions_route" {
  api_id    = aws_apigatewayv2_api.slack_api.id
  route_key = "POST /interactions"
  target    = "integrations/${aws_apigatewayv2_integration.interactions_integration.id}"
}

# Deployment and stage
resource "aws_apigatewayv2_stage" "slack_api_stage" {
  api_id      = aws_apigatewayv2_api.slack_api.id
  name        = var.environment
  auto_deploy = true
}

# Allow Lambda to be invoked by API Gateway
resource "aws_lambda_permission" "commands_permission" {
  statement_id  = "AllowAPIGInvocationCommands"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.slack_commands.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.slack_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "interactions_permission" {
  statement_id  = "AllowAPIGInvocationInteractions"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.slack_interactions.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.slack_api.execution_arn}/*/*"
}

output "slack_api_invoke_url" {
  description = "Base URL for Slack to call. For slash commands and interactions, append /commands or /interactions"
  value       = "${aws_apigatewayv2_api.slack_api.api_endpoint}/${var.environment}"
}
