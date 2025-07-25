#!/usr/bin/env python3
"""
対話形式でQ&Aシステムをデモするスクリプト
"""

import sys
import os
sys.path.append('/Users/haruka.nagashima/Develop/bedrock')

from bedrock_qa_system import BedrockKnowledgeBaseQA
import json

def interactive_demo():
    """対話形式でQ&Aシステムをデモ"""
    
    print("AWS Bedrock Knowledge Base Q&Aシステム")
    print("=" * 50)
    print("質問を入力してください（'quit'で終了）")
    print()
    
    try:
        # Q&Aシステムを初期化
        qa_system = BedrockKnowledgeBaseQA()
        print("システムが正常に初期化されました")
        print()
        
        while True:
            try:
                # 質問を入力
                question = input("質問: ")
                
                if question.lower() in ['quit', 'exit', '終了']:
                    print("さようなら！")
                    break
                
                if not question.strip():
                    continue
                
                print("回答を生成中...")
                
                # 質問に回答
                result = qa_system.ask_question(question)
                
                # 結果を表示
                print()
                print("回答:", result['answer'])
                print(f"信頼度: {result['confidence']:.3f}")
                print(f"参考ソース: {len(result['sources'])}件")
                
                # 詳細な参考ソースを表示
                if result['sources']:
                    print("\n参考ソース詳細:")
                    for i, source in enumerate(result['sources'][:3], 1):
                        filename = source['uri'].split('/')[-1]
                        print(f"  {i}. {filename} (スコア: {source['score']:.3f})")
                
                print("\n" + "-" * 50)
                
            except KeyboardInterrupt:
                print("\nさようなら！")
                break
            except Exception as e:
                print(f"エラーが発生しました: {e}")
                print("もう一度お試しください。")
                
    except Exception as e:
        print(f"システムの初期化に失敗しました: {e}")
        print("設定を確認してください。")

if __name__ == "__main__":
    interactive_demo()