resource "aws_iam_role" "lambda_exec" {
  name = "lambda-processor-role-${local.suffix}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" } }]
  })
}
resource "aws_iam_policy_attachment" "basic_exec" {
  name       = "lambda-basic-exec-${local.suffix}"
  roles      = [aws_iam_role.lambda_exec.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
resource "aws_iam_role_policy" "custom" {
  name = "lambda-custom-policy-${local.suffix}"
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      { Sid = "S3Access", Effect = "Allow",
        Action = ["s3:ListBucket","s3:GetObject","s3:HeadObject","s3:PutObject"],
        Resource = [
          aws_s3_bucket.input.arn, 
          "${aws_s3_bucket.input.arn}/*", 
          aws_s3_bucket.output.arn, 
          "${aws_s3_bucket.output.arn}/*"]

        # Resource = [
        #  # permissão de bucket (ListBucket)
        #   aws_s3_bucket.input_bucket.arn,
        #   aws_s3_bucket.output_bucket.arn,
        #   # permissão de objeto
        #   "${aws_s3_bucket.input_bucket.arn}/*",
        #   "${aws_s3_bucket.output_bucket.arn}/*"
        # ]
        },
      { Sid = "SQSAccess", Effect = "Allow", Action = ["sqs:ReceiveMessage","sqs:DeleteMessage","sqs:GetQueueAttributes"], Resource = aws_sqs_queue.proc.arn },
      { Sid = "DDBAccess", Effect = "Allow", Action = ["dynamodb:PutItem","dynamodb:UpdateItem"], Resource = aws_dynamodb_table.jobs.arn },
      { Sid = "SNSAccess", Effect = "Allow", Action = "sns:Publish", Resource = aws_sns_topic.complete.arn }
    ]
  })
}