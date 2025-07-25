#!/usr/bin/env python3
"""
インデックスを作成してからKnowledge Baseを作成するスクリプト
"""

import boto3
import json
import time
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from botocore.exceptions import ClientError

def create_opensearch_index_with_client():
    """OpenSearchクライアントを使用してインデックスを作成"""
    
    # AWS認証
    session = boto3.Session()
    credentials = session.get_credentials()
    region = 'us-east-1'
    service = 'aoss'
    
    auth = AWSV4SignerAuth(credentials, region, service)
    
    # OpenSearchクライアント
    client = OpenSearch(
        hosts=[{'host': 'wcl8a3afcpsydoomrhg2.us-east-1.aoss.amazonaws.com', 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20,
    )
    
    # インデックスマッピング
    index_body = {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 512
            }
        },
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1536,
                    "method": {
                        "name": "hnsw",
                        "space_type": "l2",
                        "engine": "faiss"
                    }
                },
                "AMAZON_BEDROCK_TEXT_CHUNK": {
                    "type": "text"
                },
                "AMAZON_BEDROCK_METADATA": {
                    "type": "text"
                }
            }
        }
    }
    
    try:
        # インデックスが存在するかチェック
        if client.indices.exists(index="bedrock-knowledge-base-default-index"):
            print("Index already exists, deleting...")
            client.indices.delete(index="bedrock-knowledge-base-default-index")
        
        # インデックスを作成
        print("Creating index...")
        response = client.indices.create(
            index="bedrock-knowledge-base-default-index",
            body=index_body
        )
        
        print(f"Index created successfully: {response}")
        return True
        
    except Exception as e:
        print(f"Error creating index: {e}")
        return False

def create_knowledge_base():
    """Knowledge Baseを作成"""
    
    # AWSクライアントを初期化
    bedrock_agent = boto3.client('bedrock-agent', region_name='us-east-1')
    
    # 設定値
    kb_name = "bedrock-kb-qa"
    kb_description = "Q&A system using crawled HTML content"
    role_arn = "arn:aws:iam::279511116447:role/bedrock-kb-qa-kb-role"
    s3_bucket = "bedrock-kb-qa-data-f501c9ff647296c6"
    collection_arn = "arn:aws:aoss:us-east-1:279511116447:collection/wcl8a3afcpsydoomrhg2"
    
    try:
        # Knowledge Baseを作成
        print("Creating Knowledge Base...")
        response = bedrock_agent.create_knowledge_base(
            name=kb_name,
            description=kb_description,
            roleArn=role_arn,
            knowledgeBaseConfiguration={
                'type': 'VECTOR',
                'vectorKnowledgeBaseConfiguration': {
                    'embeddingModelArn': 'arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1'
                }
            },
            storageConfiguration={
                'type': 'OPENSEARCH_SERVERLESS',
                'opensearchServerlessConfiguration': {
                    'collectionArn': collection_arn,
                    'vectorIndexName': 'bedrock-knowledge-base-default-index',
                    'fieldMapping': {
                        'vectorField': 'bedrock-knowledge-base-default-vector',
                        'textField': 'AMAZON_BEDROCK_TEXT_CHUNK',
                        'metadataField': 'AMAZON_BEDROCK_METADATA'
                    }
                }
            }
        )
        
        knowledge_base_id = response['knowledgeBase']['knowledgeBaseId']
        print(f"Knowledge Base created successfully! ID: {knowledge_base_id}")
        
        # 作成完了を待機
        print("Waiting for Knowledge Base to be ready...")
        while True:
            kb_response = bedrock_agent.get_knowledge_base(knowledgeBaseId=knowledge_base_id)
            status = kb_response['knowledgeBase']['status']
            print(f"Status: {status}")
            
            if status == 'ACTIVE':
                print("Knowledge Base is ready!")
                break
            elif status == 'FAILED':
                print("Knowledge Base creation failed!")
                return None
            
            time.sleep(10)
        
        return knowledge_base_id
        
    except ClientError as e:
        print(f"Error creating Knowledge Base: {e}")
        return None

def main():
    """メイン処理"""
    
    print("Step 1: Creating OpenSearch index...")
    if not create_opensearch_index_with_client():
        print("Failed to create index")
        return
    
    print("\nStep 2: Creating Knowledge Base...")
    kb_id = create_knowledge_base()
    
    if kb_id:
        print(f"\nKnowledge Base created successfully! ID: {kb_id}")
        
        # .envファイルを更新
        print("Updating .env file...")
        env_path = "/Users/haruka.nagashima/Develop/bedrock/.env"
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        with open(env_path, 'w') as f:
            for line in lines:
                if line.startswith('KNOWLEDGE_BASE_ID='):
                    f.write(f'KNOWLEDGE_BASE_ID={kb_id}\n')
                else:
                    f.write(line)
        
        print("Setup complete!")
    else:
        print("Failed to create Knowledge Base")

if __name__ == "__main__":
    main()