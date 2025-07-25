# Lambda@Edge function for Basic Authentication
resource "aws_lambda_function" "basic_auth" {
  provider         = aws.us_east_1  # Lambda@Edge must be in us-east-1
  filename         = "basic_auth.zip"
  function_name    = "${local.project_name}-basic-auth"
  role            = aws_iam_role.lambda_edge_role.arn
  handler         = "index.handler"
  source_code_hash = data.archive_file.basic_auth_zip.output_base64sha256
  runtime         = "nodejs18.x"
  timeout         = 5

  tags = local.tags

  depends_on = [
    aws_iam_role_policy_attachment.lambda_edge_logs,
    aws_cloudwatch_log_group.lambda_edge,
  ]
}

# Archive file for Lambda@Edge function
data "archive_file" "basic_auth_zip" {
  type        = "zip"
  output_path = "basic_auth.zip"
  source {
    content = <<EOF
'use strict';

exports.handler = (event, context, callback) => {
    // Get request and request headers
    const request = event.Records[0].cf.request;
    const headers = request.headers;

    // Configure authentication
    const authUser = 'wovn-admin';
    const authPass = 'WPv6sVYE';

    // Construct the Basic Auth string
    const authString = 'Basic ' + Buffer.from(authUser + ':' + authPass).toString('base64');

    // Require Basic authentication
    if (typeof headers.authorization == 'undefined' || headers.authorization[0].value != authString) {
        const body = 'Unauthorized';
        const response = {
            status: '401',
            statusDescription: 'Unauthorized',
            body: body,
            headers: {
                'www-authenticate': [{key: 'WWW-Authenticate', value:'Basic'}]
            },
        };
        callback(null, response);
    }

    // Continue request processing if authentication passed
    callback(null, request);
};
EOF
    filename = "index.js"
  }
}

# Provider for us-east-1 (required for Lambda@Edge)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

# IAM role for Lambda@Edge
resource "aws_iam_role" "lambda_edge_role" {
  name = "${local.project_name}-lambda-edge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = [
            "lambda.amazonaws.com",
            "edgelambda.amazonaws.com"
          ]
        }
      }
    ]
  })

  tags = local.tags
}

# CloudWatch Logs group for Lambda@Edge
resource "aws_cloudwatch_log_group" "lambda_edge" {
  provider          = aws.us_east_1
  name              = "/aws/lambda/us-east-1.${local.project_name}-basic-auth"
  retention_in_days = 14

  tags = local.tags
}

# IAM policy attachment for Lambda@Edge logs
resource "aws_iam_role_policy_attachment" "lambda_edge_logs" {
  role       = aws_iam_role.lambda_edge_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Update CloudFront distribution to include Lambda@Edge
resource "aws_cloudfront_distribution" "web_interface_with_auth" {
  depends_on = [aws_lambda_function.basic_auth]

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
  comment             = "${local.project_name} web interface distribution with Basic Auth"

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
      lambda_arn   = aws_lambda_function.basic_auth.qualified_arn
      include_body = false
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  # Cache behavior for JavaScript files
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
    default_ttl = 300
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

  # Replace the original distribution
  lifecycle {
    replace_triggered_by = [
      aws_lambda_function.basic_auth
    ]
  }
}