resource "aws_s3_bucket" "input" {
  bucket = "${var.input_bucket_name}-${local.suffix}"
}
resource "aws_s3_bucket_lifecycle_configuration" "input_lc" {
  bucket = aws_s3_bucket.input.id
  rule { 
    id = "expire-30d" 
    status = "Enabled" 
    expiration { days = 30 } 
    }
}
resource "aws_s3_bucket" "output" {
  bucket = "${var.output_bucket_name}-${local.suffix}"
}
resource "aws_s3_bucket_lifecycle_configuration" "output_lc" {
  bucket = aws_s3_bucket.output.id
  rule { 
    id = "expire-7d" 
    status = "Enabled" 
    expiration { days = 7 } 
    }
}
resource "aws_s3_bucket_notification" "to_sqs" {
  bucket = aws_s3_bucket.input.id
  queue {
    queue_arn = aws_sqs_queue.proc.arn
    events    = ["s3:ObjectCreated:*"]
  }
  depends_on = [aws_sqs_queue_policy.allow_s3]
}