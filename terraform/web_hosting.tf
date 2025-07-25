# Random ID for web bucket name uniqueness
resource "random_id" "web_bucket_suffix" {
  byte_length = 4
}

# S3 Bucket for Web Interface hosting
resource "aws_s3_bucket" "web_interface" {
  bucket = "${local.project_name}-web-interface-${random_id.web_bucket_suffix.hex}"
  tags   = local.tags
}

# S3 Bucket versioning for web interface
resource "aws_s3_bucket_versioning" "web_interface_versioning" {
  bucket = aws_s3_bucket.web_interface.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket website configuration
resource "aws_s3_bucket_website_configuration" "web_interface_website" {
  bucket = aws_s3_bucket.web_interface.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

# S3 Bucket public access block (allow public access for CloudFront)
resource "aws_s3_bucket_public_access_block" "web_interface_pab" {
  bucket = aws_s3_bucket.web_interface.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# S3 Bucket policy for CloudFront access
resource "aws_s3_bucket_policy" "web_interface_policy" {
  bucket     = aws_s3_bucket.web_interface.id
  depends_on = [aws_s3_bucket_public_access_block.web_interface_pab]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontAccess"
        Effect    = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.web_interface_oai.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.web_interface.arn}/*"
      }
    ]
  })
}

# CloudFront Origin Access Identity
resource "aws_cloudfront_origin_access_identity" "web_interface_oai" {
  comment = "OAI for ${local.project_name} web interface"
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "web_interface" {
  origin {
    domain_name = aws_s3_bucket.web_interface.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.web_interface.bucket}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.web_interface_oai.cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "${local.project_name} web interface distribution"

  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.web_interface.bucket}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    # Add Lambda@Edge function for Basic Authentication
    lambda_function_association {
      event_type   = "viewer-request"
      lambda_arn   = "arn:aws:lambda:us-east-1:279511116447:function:bedrock-kb-qa-basic-auth:2"
      include_body = false
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  # Cache behavior for JavaScript files (minimal caching for development)
  ordered_cache_behavior {
    path_pattern           = "*.js"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.web_interface.bucket}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 300  # 5 minutes
    max_ttl     = 3600
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = local.tags
}

# Upload web interface HTML file
resource "aws_s3_object" "web_interface_html" {
  bucket       = aws_s3_bucket.web_interface.id
  key          = "index.html"
  source       = "../examples/web_interface.html"
  etag         = filemd5("../examples/web_interface.html")
  content_type = "text/html"
  tags         = local.tags
}

# Create a simple error page
resource "aws_s3_object" "error_page" {
  bucket       = aws_s3_bucket.web_interface.id
  key          = "error.html"
  content_type = "text/html"
  content = <<EOF
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page Not Found - WOVN.io Knowledge Base</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #40b87c 0%, #2d8a5f 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            max-width: 500px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }
        h1 {
            color: #2c3e50;
            font-size: 2em;
            margin-bottom: 20px;
        }
        p {
            color: #7f8c8d;
            font-size: 1.1em;
            margin-bottom: 30px;
        }
        a {
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            text-decoration: none;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 16px;
            transition: transform 0.2s ease;
        }
        a:hover {
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>404 - ページが見つかりません</h1>
        <p>お探しのページは存在しないか、移動された可能性があります。</p>
        <a href="/">ホームに戻る</a>
    </div>
</body>
</html>
EOF
  tags = local.tags
}