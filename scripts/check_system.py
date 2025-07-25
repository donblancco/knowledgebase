#!/usr/bin/env python3
"""
システムの状態を確認するスクリプト
"""

import boto3
import os
import json
from dotenv import load_dotenv

def check_system_status():
    """システムの状態を確認"""
    
    print("🔍 AWS Bedrock Knowledge Base システム状態確認")
    print("=" * 60)
    
    # 環境変数の確認
    load_dotenv()
    
    print("1. 環境変数の確認")
    print("-" * 30)
    
    required_vars = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY', 
        'AWS_REGION',
        'KNOWLEDGE_BASE_ID',
        'BEDROCK_MODEL_ID'
    ]
    
    env_ok = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            masked_value = value[:4] + '*' * (len(value) - 4) if len(value) > 4 else '*' * len(value)
            print(f"  ✅ {var}: {masked_value}")
        else:
            print(f"  ❌ {var}: 設定されていません")
            env_ok = False
    
    print()
    
    if not env_ok:
        print("❌ 環境変数が正しく設定されていません")
        return False
    
    # AWS接続の確認
    print("2. AWS接続の確認")
    print("-" * 30)
    
    try:
        # STS (AWS Security Token Service) で認証確認
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        print(f"  ✅ AWSユーザー: {identity['Arn']}")
        print(f"  ✅ アカウントID: {identity['Account']}")
    except Exception as e:
        print(f"  ❌ AWS接続エラー: {e}")
        return False
    
    print()
    
    # Knowledge Base の確認
    print("3. Knowledge Base の確認")
    print("-" * 30)
    
    try:
        bedrock_agent = boto3.client('bedrock-agent', region_name=os.getenv('AWS_REGION'))
        kb_id = os.getenv('KNOWLEDGE_BASE_ID')
        
        kb_info = bedrock_agent.get_knowledge_base(knowledgeBaseId=kb_id)
        kb = kb_info['knowledgeBase']
        
        print(f"  ✅ Knowledge Base名: {kb['name']}")
        print(f"  ✅ 状態: {kb['status']}")
        print(f"  ✅ 埋め込みモデル: {kb['knowledgeBaseConfiguration']['vectorKnowledgeBaseConfiguration']['embeddingModelArn'].split('/')[-1]}")
        
        # データソースの確認
        try:
            data_sources = bedrock_agent.list_data_sources(knowledgeBaseId=kb_id)
            print(f"  ✅ データソース数: {len(data_sources['dataSourceSummaries'])}")
            
            for ds in data_sources['dataSourceSummaries']:
                print(f"    - {ds['name']}: {ds['status']}")
        except Exception as e:
            print(f"  ⚠️  データソース確認エラー: {e}")
            
    except Exception as e:
        print(f"  ❌ Knowledge Base確認エラー: {e}")
        return False
    
    print()
    
    # Bedrockモデルアクセスの確認
    print("4. Bedrockモデルアクセスの確認")
    print("-" * 30)
    
    try:
        bedrock_client = boto3.client('bedrock', region_name=os.getenv('AWS_REGION'))
        
        # 利用可能なモデルを確認
        models = bedrock_client.list_foundation_models()
        
        model_id = os.getenv('BEDROCK_MODEL_ID')
        available_models = [m['modelId'] for m in models['modelSummaries']]
        
        if model_id in available_models:
            print(f"  ✅ 回答生成モデル: {model_id}")
        else:
            print(f"  ❌ 回答生成モデル '{model_id}' が利用できません")
            
        # 埋め込みモデルの確認
        embed_models = [m for m in models['modelSummaries'] if 'embed' in m['modelId']]
        if embed_models:
            print(f"  ✅ 埋め込みモデル数: {len(embed_models)}")
        else:
            print(f"  ⚠️  埋め込みモデルが見つかりません")
            
    except Exception as e:
        print(f"  ❌ Bedrockモデル確認エラー: {e}")
        return False
    
    print()
    
    # S3データの確認
    print("5. S3データの確認")
    print("-" * 30)
    
    try:
        s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION'))
        
        # S3バケットの確認
        bucket_name = "bedrock-kb-qa-data-f501c9ff647296c6"
        
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix='html/',
                MaxKeys=1000
            )
            
            if 'Contents' in response:
                file_count = len(response['Contents'])
                print(f"  ✅ S3バケット: {bucket_name}")
                print(f"  ✅ HTMLファイル数: {file_count}")
            else:
                print(f"  ⚠️  S3バケット '{bucket_name}' にファイルが見つかりません")
                
        except Exception as e:
            print(f"  ❌ S3バケット確認エラー: {e}")
            
    except Exception as e:
        print(f"  ❌ S3確認エラー: {e}")
        return False
    
    print()
    
    # 簡単なテスト実行
    print("6. 簡単なテスト実行")
    print("-" * 30)
    
    try:
        # Q&Aシステムのテスト
        from bedrock_qa_system import BedrockKnowledgeBaseQA
        
        qa_system = BedrockKnowledgeBaseQA()
        test_result = qa_system.ask_question("こんにちは")
        
        if test_result and test_result.get('answer'):
            print("  ✅ Q&Aシステムのテスト成功")
            print(f"  ✅ 回答: {test_result['answer'][:50]}...")
            print(f"  ✅ 信頼度: {test_result['confidence']:.3f}")
        else:
            print("  ❌ Q&Aシステムのテスト失敗")
            return False
            
    except Exception as e:
        print(f"  ❌ テスト実行エラー: {e}")
        return False
    
    print()
    print("🎉 システムは正常に動作しています！")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    check_system_status()