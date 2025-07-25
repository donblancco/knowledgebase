#!/usr/bin/env python3
"""
OpenSearch Serverlessにインデックスを作成するスクリプト
"""

import boto3
import json
import time
import requests
from requests.auth import HTTPBasicAuth
from botocore.exceptions import ClientError

def create_opensearch_index():
    """OpenSearchインデックスを作成"""
    
    # OpenSearchクライアント
    opensearch_client = boto3.client('opensearchserverless', region_name='us-east-1')
    
    # コレクション情報を取得
    collection_id = "wcl8a3afcpsydoomrhg2"
    collection_name = "bedrock-kb-qa-collection"
    
    # OpenSearch Serverlessエンドポイント
    endpoint = f"https://{collection_id}.us-east-1.aoss.amazonaws.com"
    
    # インデックス作成のマッピング
    index_mapping = {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 512,
                "knn.algo_param.ef_construction": 512
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
        # AWS認証情報を取得
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # OpenSearch Serverlessにインデックスを作成
        index_url = f"{endpoint}/bedrock-knowledge-base-default-index"
        
        print(f"Creating index at: {index_url}")
        
        # AWS SigV4認証を使用
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest
        
        request = AWSRequest(
            method='PUT',
            url=index_url,
            data=json.dumps(index_mapping),
            headers={'Content-Type': 'application/json'}
        )
        
        SigV4Auth(credentials, 'aoss', 'us-east-1').add_auth(request)
        
        # リクエストを送信
        response = requests.put(
            index_url,
            data=json.dumps(index_mapping),
            headers=dict(request.headers)
        )
        
        if response.status_code in [200, 201]:
            print("Index created successfully!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"Error creating index: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error creating index: {e}")
        return False

if __name__ == "__main__":
    create_opensearch_index()