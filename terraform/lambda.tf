# IAM Role for Lambda execution
resource "aws_iam_role" "lambda_exec" {
  name               = "${var.prefix}-lambdaRole-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_dynamodb_policy" {
  name   = "${var.prefix}-lambdaDynamoDBPolicy-${var.environment}"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_dynamodb_access.json
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "lambda_dynamodb_access" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
      "dynamodb:Scan"
    ]
    resources = [
      aws_dynamodb_table.incidents.arn,
      "${aws_dynamodb_table.incidents.arn}/index/*"
    ]
  }
}


resource "aws_lambda_function" "slack_commands" {
  function_name    = "${var.prefix}-commands-${var.environment}"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "main.handler"
  runtime          = "python3.9"
  filename         = "${path.module}/../lambdas_build/commands.zip"
  timeout          = 15

  environment {
    variables = {
      SLACK_SIGNING_SECRET     = var.slack_signing_secret
      SLACK_VERIFICATION_TOKEN = var.slack_verification_token
      SLACK_BOT_TOKEN          = var.slack_bot_token
      DYNAMODB_TABLE_NAME      = aws_dynamodb_table.incidents.name
      ENVIRONMENT              = var.environment
    }
  }
}

resource "aws_lambda_function" "slack_interactions" {
  function_name    = "${var.prefix}-interactions-${var.environment}"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "main.handler"
  runtime          = "python3.9"
  filename         = "${path.module}/../lambdas_build/interactions.zip"
  timeout          = 15

  environment {
    variables = {
      SLACK_SIGNING_SECRET     = var.slack_signing_secret
      SLACK_VERIFICATION_TOKEN = var.slack_verification_token
      SLACK_BOT_TOKEN          = var.slack_bot_token
      DYNAMODB_TABLE_NAME      = aws_dynamodb_table.incidents.name
      ENVIRONMENT              = var.environment
    }
  }
}
