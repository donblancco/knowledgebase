#!/usr/bin/env python3
"""
Knowledge Baseのデータソース同期を開始するスクリプト
"""

import boto3
import time
from botocore.exceptions import ClientError

def start_ingestion():
    """データソースの同期を開始"""
    
    bedrock_agent = boto3.client('bedrock-agent', region_name='us-east-1')
    
    knowledge_base_id = "EZBGMFGO50"
    data_source_id = "JYQYIWFOO1"
    
    try:
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
                # 統計情報を表示
                statistics = job_response['ingestionJob'].get('statistics', {})
                print(f"Statistics: {statistics}")
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
        
    except ClientError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    start_ingestion()