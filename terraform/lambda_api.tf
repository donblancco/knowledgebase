# Lambda function for Q&A API
resource "aws_lambda_function" "qa_api" {
  function_name = "${local.project_name}-qa-api"
  role         = aws_iam_role.lambda_role.arn
  handler      = "lambda_handler.lambda_handler"
  runtime      = "python3.9"
  timeout      = 30
  memory_size  = 512

  filename         = "../lambda_deployment.zip"
  source_code_hash = filebase64sha256("../lambda_deployment.zip")

  environment {
    variables = {
      KNOWLEDGE_BASE_ID = aws_bedrockagent_knowledge_base.main.id
      BEDROCK_MODEL_ID  = var.bedrock_model_id
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_logs,
    aws_iam_role_policy_attachment.lambda_bedrock,
    aws_cloudwatch_log_group.lambda_logs,
  ]

  tags = local.tags
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${local.project_name}-qa-api"
  retention_in_days = 7
  tags              = local.tags
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${local.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.tags
}

# IAM Policy for Lambda logging
resource "aws_iam_policy" "lambda_logging" {
  name = "${local.project_name}-lambda-logging"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# IAM Policy for Lambda Bedrock access
resource "aws_iam_policy" "lambda_bedrock" {
  name = "${local.project_name}-lambda-bedrock"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:GetKnowledgeBase",
          "bedrock:Retrieve",
          "bedrock-agent:GetKnowledgeBase",
          "bedrock-agent:RetrieveAndGenerate"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock-agent:Retrieve",
          "bedrock-agent-runtime:Retrieve",
          "bedrock-agent-runtime:RetrieveAndGenerate"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach policies to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_role_policy_attachment" "lambda_bedrock" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_bedrock.arn
}

# API Gateway REST API
resource "aws_api_gateway_rest_api" "qa_api" {
  name        = "${local.project_name}-api"
  description = "Q&A API using AWS Bedrock Knowledge Base"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = local.tags
}

# API Gateway Resource
resource "aws_api_gateway_resource" "ask" {
  rest_api_id = aws_api_gateway_rest_api.qa_api.id
  parent_id   = aws_api_gateway_rest_api.qa_api.root_resource_id
  path_part   = "ask"
}

# API Gateway Method (POST)
resource "aws_api_gateway_method" "ask_post" {
  rest_api_id   = aws_api_gateway_rest_api.qa_api.id
  resource_id   = aws_api_gateway_resource.ask.id
  http_method   = "POST"
  authorization = "NONE"
}

# API Gateway Method (OPTIONS for CORS)
resource "aws_api_gateway_method" "ask_options" {
  rest_api_id   = aws_api_gateway_rest_api.qa_api.id
  resource_id   = aws_api_gateway_resource.ask.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# API Gateway Integration (POST)
resource "aws_api_gateway_integration" "ask_integration" {
  rest_api_id = aws_api_gateway_rest_api.qa_api.id
  resource_id = aws_api_gateway_resource.ask.id
  http_method = aws_api_gateway_method.ask_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.qa_api.invoke_arn
}

# API Gateway Integration (OPTIONS for CORS)
resource "aws_api_gateway_integration" "ask_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.qa_api.id
  resource_id = aws_api_gateway_resource.ask.id
  http_method = aws_api_gateway_method.ask_options.http_method

  type = "MOCK"
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# API Gateway Method Response (POST)
resource "aws_api_gateway_method_response" "ask_response_200" {
  rest_api_id = aws_api_gateway_rest_api.qa_api.id
  resource_id = aws_api_gateway_resource.ask.id
  http_method = aws_api_gateway_method.ask_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# API Gateway Method Response (OPTIONS)
resource "aws_api_gateway_method_response" "ask_options_response_200" {
  rest_api_id = aws_api_gateway_rest_api.qa_api.id
  resource_id = aws_api_gateway_resource.ask.id
  http_method = aws_api_gateway_method.ask_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# API Gateway Integration Response (OPTIONS)
resource "aws_api_gateway_integration_response" "ask_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.qa_api.id
  resource_id = aws_api_gateway_resource.ask.id
  http_method = aws_api_gateway_method.ask_options.http_method
  status_code = aws_api_gateway_method_response.ask_options_response_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gateway_lambda" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.qa_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.qa_api.execution_arn}/*/*"
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "qa_api_deployment" {
  depends_on = [
    aws_api_gateway_integration.ask_integration,
    aws_api_gateway_integration.ask_options_integration,
  ]

  rest_api_id = aws_api_gateway_rest_api.qa_api.id

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage
resource "aws_api_gateway_stage" "qa_api_stage" {
  deployment_id = aws_api_gateway_deployment.qa_api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.qa_api.id
  stage_name    = var.environment

  tags = local.tags
}