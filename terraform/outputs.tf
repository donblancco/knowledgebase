output "s3_bucket_name" {
  description = "Name of the S3 bucket (use in AWS Console)"
  value       = aws_s3_bucket.kb_data.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket (use in AWS Console)"
  value       = aws_s3_bucket.kb_data.arn
}

output "iam_role_arn" {
  description = "ARN of the IAM role (use in AWS Console)"
  value       = aws_iam_role.kb_role.arn
}

output "knowledge_base_id" {
  description = "Knowledge Base ID"
  value       = aws_bedrockagent_knowledge_base.main.id
}

output "api_gateway_url" {
  description = "API Gateway URL"
  value       = "https://${aws_api_gateway_rest_api.qa_api.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.qa_api_stage.stage_name}"
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.qa_api.function_name
}

output "web_bucket_name" {
  description = "Web interface S3 bucket name"
  value       = aws_s3_bucket.web_interface.bucket
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.web_interface.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.web_interface.id
}

output "web_interface_url" {
  description = "Web interface URL"
  value       = "https://${aws_cloudfront_distribution.web_interface.domain_name}"
}

output "setup_complete" {
  description = "Setup completion message"
  value = <<-EOT
  
  Knowledge Base setup complete!
  
  Knowledge Base ID: ${aws_bedrockagent_knowledge_base.main.id}
  API Gateway URL: https://${aws_api_gateway_rest_api.qa_api.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.qa_api_stage.stage_name}
  Web Interface URL: https://${aws_cloudfront_distribution.web_interface.domain_name}
  
  .envファイルに以下を設定してください：
  KNOWLEDGE_BASE_ID=${aws_bedrockagent_knowledge_base.main.id}
  
  API使用例：
  curl -X POST https://${aws_api_gateway_rest_api.qa_api.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.qa_api_stage.stage_name}/ask \\
    -H "Content-Type: application/json" \\
    -d '{"question": "WOVN.ioのサイト内検索について教えて"}'
  
  Web Interface：
  ブラウザで https://${aws_cloudfront_distribution.web_interface.domain_name} にアクセス
  
  EOT
}