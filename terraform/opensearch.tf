# OpenSearch Serverless collection for Knowledge Base
resource "aws_opensearchserverless_security_policy" "kb_security_policy" {
  name = "${local.project_name}-security-policy"
  type = "encryption"
  
  policy = jsonencode({
    "Rules" = [
      {
        "Resource" = [
          "collection/kb-*"
        ]
        "ResourceType" = "collection"
      }
    ]
    "AWSOwnedKey" = true
  })
}

resource "aws_opensearchserverless_security_policy" "kb_network_policy" {
  name = "${local.project_name}-network-policy"
  type = "network"
  
  policy = jsonencode([
    {
      "Rules" = [
        {
          "Resource" = [
            "collection/kb-*"
          ]
          "ResourceType" = "collection"
        }
      ]
      "AllowFromPublic" = true
    }
  ])
}

resource "aws_opensearchserverless_access_policy" "knowledge_base_access_policy" {
  name = "${local.project_name}-access-policy"
  type = "data"
  
  policy = jsonencode([
    {
      "Rules" = [
        {
          "Resource" = [
            "collection/kb-*"
          ]
          "Permission" = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
          "ResourceType" = "collection"
        },
        {
          "Resource" = [
            "index/kb-*/*"
          ]
          "Permission" = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
          "ResourceType" = "index"
        }
      ]
      "Principal" = [
        aws_iam_role.kb_role.arn
      ]
    }
  ])
}

resource "aws_opensearchserverless_collection" "knowledge_base_collection" {
  name = "kb-${random_id.bucket_suffix.hex}"
  type = "VECTORSEARCH"
  
  depends_on = [
    aws_opensearchserverless_security_policy.kb_security_policy,
    aws_opensearchserverless_security_policy.kb_network_policy,
    aws_opensearchserverless_access_policy.knowledge_base_access_policy
  ]
  
  tags = local.tags
}

# OpenSearch policy for Knowledge Base IAM role
resource "aws_iam_policy" "kb_opensearch_policy" {
  name = "${local.project_name}-kb-opensearch-policy"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = [
          aws_opensearchserverless_collection.knowledge_base_collection.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "kb_opensearch_attachment" {
  role       = aws_iam_role.kb_role.name
  policy_arn = aws_iam_policy.kb_opensearch_policy.arn
}


# Knowledge Base with OpenSearch
resource "aws_bedrockagent_knowledge_base" "main" {
  name     = var.knowledge_base_name
  role_arn = aws_iam_role.kb_role.arn
  
  knowledge_base_configuration {
    vector_knowledge_base_configuration {
      embedding_model_arn = var.embedding_model_arn
    }
    type = "VECTOR"
  }
  
  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = "arn:aws:aoss:us-east-1:279511116447:collection/zygdkqlpnhvu9j8yqms6"
      vector_index_name = "bedrock-knowledge-base-default-index"
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }
  
  tags = local.tags
  
  depends_on = [
    aws_iam_role_policy_attachment.kb_opensearch_attachment,
    aws_opensearchserverless_collection.knowledge_base_collection
  ]
}

# Data Source for Knowledge Base
resource "aws_bedrockagent_data_source" "main" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.main.id
  name              = "s3-data-source"
  
  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.kb_data.arn
    }
  }
  
  depends_on = [
    aws_bedrockagent_knowledge_base.main,
    aws_s3_object.data
  ]
}