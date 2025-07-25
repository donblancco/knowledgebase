terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  project_name = "bedrock-kb-qa"
  tags = {
    Project     = local.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Random ID for bucket name uniqueness
resource "random_id" "bucket_suffix" {
  byte_length = 8
}

# S3 Bucket for Knowledge Base data
resource "aws_s3_bucket" "kb_data" {
  bucket = "${local.project_name}-data-${random_id.bucket_suffix.hex}"
  tags   = local.tags
}

resource "aws_s3_bucket_versioning" "kb_data_versioning" {
  bucket = aws_s3_bucket.kb_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "kb_data_pab" {
  bucket = aws_s3_bucket.kb_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Upload sample data
resource "aws_s3_object" "data" {
  bucket = aws_s3_bucket.kb_data.id
  key    = "helppage.csv"
  source = "../srcfile/helppage.csv"
  etag   = filemd5("../srcfile/helppage.csv")
  tags   = local.tags
}

# IAM Role for Knowledge Base
resource "aws_iam_role" "kb_role" {
  name = "${local.project_name}-kb-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
      }
    ]
  })

  tags = local.tags
}

# IAM Policy for S3 access
resource "aws_iam_policy" "kb_s3_policy" {
  name = "${local.project_name}-kb-s3-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.kb_data.arn,
          "${aws_s3_bucket.kb_data.arn}/*"
        ]
      }
    ]
  })
}

# IAM Policy for Bedrock models
resource "aws_iam_policy" "kb_bedrock_policy" {
  name = "${local.project_name}-kb-bedrock-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          var.embedding_model_arn
        ]
      }
    ]
  })
}

# Attach policies to role
resource "aws_iam_role_policy_attachment" "kb_s3_attachment" {
  role       = aws_iam_role.kb_role.name
  policy_arn = aws_iam_policy.kb_s3_policy.arn
}

resource "aws_iam_role_policy_attachment" "kb_bedrock_attachment" {
  role       = aws_iam_role.kb_role.name
  policy_arn = aws_iam_policy.kb_bedrock_policy.arn
}