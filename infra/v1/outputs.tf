output "input_bucket" {
  description = "Name of the input S3 bucket"
  value       = aws_s3_bucket.input.bucket
}

output "output_bucket" {
  description = "Name of the output S3 bucket"
  value       = aws_s3_bucket.output.bucket
}

output "sqs_queue_url" {
  description = "URL of the SQS processing queue"
  value       = aws_sqs_queue.proc.id
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB jobs table"
  value       = aws_dynamodb_table.jobs.name
}

output "sns_topic_arn" {
  description = "ARN of the SNS completion topic"
  value       = aws_sns_topic.complete.arn
}

output "lambda_function_name" {
  description = "Name of the video-processor Lambda function"
  value       = aws_lambda_function.processor.function_name
}

output "lambda_function_arn" {
  description = "ARN of the video-processor Lambda function"
  value       = aws_lambda_function.processor.arn
}

