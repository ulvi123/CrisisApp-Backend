resource "aws_dynamodb_table" "incidents" {
  name           = "${var.prefix}-incidents-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "IncidentId"

  attribute {
    name = "IncidentId"
    type = "S"
  }

  attribute {
    name = "SoNumber"
    type = "S"
  }
  
  global_secondary_index {
    name               = "SoNumberIndex"
    hash_key           = "SoNumber"
    projection_type    = "ALL"
  }

  tags = {
    Environment = var.environment
    Application = "CrisisApp"
  }
}
