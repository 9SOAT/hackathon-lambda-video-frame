####################################
# Variables
####################################
variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "input_bucket_name" {
  description = "Base name for the input S3 bucket"
  type        = string
  default     = "video-input-bucket"
}

variable "output_bucket_name" {
  description = "Base name for the output S3 bucket"
  type        = string
  default     = "video-output-bucket"
}

variable "queue_name" {
  description = "Name prefix for the SQS processing queue"
  type        = string
  default     = "video-processing-queue"
}

variable "ddb_table_name" {
  description = "Name of the DynamoDB table for job metadata"
  type        = string
  default     = "video-jobs"
}

variable "sns_topic_name" {
  description = "Name of the SNS topic for job completion notifications"
  type        = string
  default     = "video-complete-topic"
}

variable "deployment_package_path" {
  description = "Local path to the zipped Lambda deployment package"
  type        = string
  default     = "./deployment-package.zip"
}

variable "lambda_timeout" {
  description = "Timeout for the Lambda function in seconds"
  type        = number
  default     = 900
}

variable "lambda_memory" {
  description = "Memory size for the Lambda function in MB"
  type        = number
  default     = 1024
}