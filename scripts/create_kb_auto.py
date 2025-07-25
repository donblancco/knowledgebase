#!/usr/bin/env python3
"""
AWS Bedrock Knowledge Baseを自動で作成するスクリプト
"""

import boto3
import json
import time
import os
from botocore.exceptions import ClientError

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
        
        # データソースを作成
        print("Creating data source...")
        ds_response = bedrock_agent.create_data_source(
            knowledgeBaseId=knowledge_base_id,
            name="html-content",
            description="Crawled HTML content from URLs",
            dataSourceConfiguration={
                'type': 'S3',
                's3Configuration': {
                    'bucketArn': f'arn:aws:s3:::{s3_bucket}',
                    'inclusionPrefixes': ['html/']
                }
            }
        )
        
        data_source_id = ds_response['dataSource']['dataSourceId']
        print(f"Data source created! ID: {data_source_id}")
        
        # データソースの同期を開始
        print("Starting data source sync...")
        sync_response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id
        )
        
        ingestion_job_id = sync_response['ingestionJob']['ingestionJobId']
        print(f"Ingestion job started! ID: {ingestion_job_id}")
        
        # 同期完了を待機
        print("Waiting for ingestion to complete...")
        while True:
            job_response = bedrock_agent.get_ingestion_job(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id,
                ingestionJobId=ingestion_job_id
            )
            status = job_response['ingestionJob']['status']
            print(f"Ingestion status: {status}")
            
            if status == 'COMPLETE':
                print("Ingestion completed successfully!")
                break
            elif status == 'FAILED':
                print("Ingestion failed!")
                print(f"Failure reasons: {job_response['ingestionJob'].get('failureReasons', [])}")
                break
            
            time.sleep(30)
        
        # .envファイルを更新
        print("Updating .env file...")
        env_path = "/Users/haruka.nagashima/Develop/bedrock/.env"
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        with open(env_path, 'w') as f:
            for line in lines:
                if line.startswith('KNOWLEDGE_BASE_ID='):
                    f.write(f'KNOWLEDGE_BASE_ID={knowledge_base_id}\n')
                else:
                    f.write(line)
        
        print(f"Setup complete! Knowledge Base ID: {knowledge_base_id}")
        return knowledge_base_id
        
    except ClientError as e:
        print(f"Error creating Knowledge Base: {e}")
        return None

if __name__ == "__main__":
    create_knowledge_base()