data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda"
  output_path = "${path.module}/../build/deployment-package.zip"
}
resource "aws_lambda_function" "processor" {
  function_name    = "video-processor-${local.suffix}"
  handler          = "lambda_processor.lambda_handler"
  runtime          = "python3.9"
  role             = aws_iam_role.lambda_exec.arn
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  #layers           = [aws_lambda_layer_version.ffmpeg.arn]
  environment {
    variables = {
      INPUT_BUCKET  = aws_s3_bucket.input.bucket
      OUTPUT_BUCKET = aws_s3_bucket.output.bucket
      DDB_TABLE     = aws_dynamodb_table.jobs.name
      SNS_TOPIC_ARN = aws_sns_topic.complete.arn
    }
  }
}
resource "aws_lambda_event_source_mapping" "sqs2lambda" {
  event_source_arn = aws_sqs_queue.proc.arn
  function_name    = aws_lambda_function.processor.arn
  batch_size       = 1
  enabled          = true
}