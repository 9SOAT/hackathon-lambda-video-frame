resource "aws_dynamodb_table" "jobs" {
  name         = var.ddb_table_name
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "user_prefix"
  range_key = "timestamp"
   attribute {
    name = "user_prefix"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }
}