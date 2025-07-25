#!/usr/bin/env python3
"""
Q&Aシステムをテストするスクリプト
"""

import sys
import os
# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bedrock_qa_system import BedrockKnowledgeBaseQA

def test_qa_system():
    """Q&Aシステムをテスト"""
    
    try:
        # Q&Aシステムを初期化
        qa_system = BedrockKnowledgeBaseQA()
        
        # テスト質問
        test_questions = [
            "こんにちは",
            "AWS Bedrockとは何ですか？",
            "Knowledge Baseの使い方を教えて"
        ]
        
        for question in test_questions:
            print(f"\n=== 質問: {question} ===")
            
            try:
                answer = qa_system.ask_question(question)
                print(f"回答: {answer}")
            except Exception as e:
                print(f"エラー: {e}")
                
    except Exception as e:
        print(f"初期化エラー: {e}")

if __name__ == "__main__":
    test_qa_system()