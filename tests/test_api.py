#!/usr/bin/env python3
"""
Lambda関数のローカルテスト用スクリプト
"""

import json
import sys
import os

# 現在のディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lambda_handler import lambda_handler

def test_lambda_handler():
    """Lambda関数をローカルでテスト"""
    
    # テスト用のイベントデータ
    test_cases = [
        {
            "name": "正常な質問",
            "event": {
                "httpMethod": "POST",
                "body": json.dumps({
                    "question": "サイト内検索について教えて",
                    "max_results": 3
                })
            }
        },
        {
            "name": "空の質問",
            "event": {
                "httpMethod": "POST",
                "body": json.dumps({
                    "question": "",
                    "max_results": 3
                })
            }
        },
        {
            "name": "不正なJSON",
            "event": {
                "httpMethod": "POST",
                "body": "invalid json"
            }
        },
        {
            "name": "OPTIONSメソッド",
            "event": {
                "httpMethod": "OPTIONS",
                "body": None
            }
        }
    ]
    
    print("Lambda関数のテストを開始します...\n")
    
    for test_case in test_cases:
        print(f"テストケース: {test_case['name']}")
        print("-" * 50)
        
        try:
            # Lambda関数を実行
            response = lambda_handler(test_case['event'], None)
            
            # レスポンスを表示
            print(f"ステータスコード: {response['statusCode']}")
            print(f"レスポンス: {response['body']}")
            
            # JSONを整形して表示
            if response['body']:
                try:
                    body = json.loads(response['body'])
                    print(f"整形されたレスポンス:")
                    print(json.dumps(body, ensure_ascii=False, indent=2))
                except json.JSONDecodeError:
                    print(f"レスポンスボディ: {response['body']}")
            
        except Exception as e:
            print(f"エラーが発生しました: {e}")
        
        print("\n" + "=" * 60 + "\n")

if __name__ == "__main__":
    test_lambda_handler()