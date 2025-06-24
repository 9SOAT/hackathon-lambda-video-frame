resource "aws_sqs_queue" "dlq" {
  name                      = "${var.queue_name}-dlq-${local.suffix}"
  message_retention_seconds = 1209600
}
resource "aws_sqs_queue" "proc" {
  name                       = var.queue_name
  visibility_timeout_seconds = var.lambda_timeout
  message_retention_seconds  = 86400
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn,
    maxReceiveCount     = 5
  })
}
resource "aws_sqs_queue_policy" "allow_s3" {
  queue_url = aws_sqs_queue.proc.id
  policy    = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Sid       = "AllowS3EventNotifications",
      Effect    = "Allow",
      Principal = { Service = "s3.amazonaws.com" },
      Action    = "sqs:SendMessage",
      Resource  = aws_sqs_queue.proc.arn,
      Condition = { ArnEquals = { "aws:SourceArn" = aws_s3_bucket.input.arn } }
    }]
  })
}
