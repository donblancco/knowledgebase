#!/usr/bin/env python3
"""
AWS Lambda Handler for Bedrock Knowledge Base Q&A API
"""

import json
import logging
import traceback
from typing import Dict, Any
from bedrock_qa_system import BedrockKnowledgeBaseQA

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# グローバル変数でQ&Aシステムを保持（コールド起動時のみ初期化）
qa_system = None

def initialize_qa_system():
    """Q&Aシステムを初期化"""
    global qa_system
    if qa_system is None:
        try:
            qa_system = BedrockKnowledgeBaseQA()
            logger.info("Q&Aシステムが正常に初期化されました")
        except Exception as e:
            logger.error(f"Q&Aシステムの初期化に失敗: {e}")
            raise

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """API Gateway用のレスポンス形式を作成"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Requested-With',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS,PUT,DELETE',
            'Access-Control-Allow-Credentials': 'false'
        },
        'body': json.dumps(body, ensure_ascii=False)
    }

def create_error_response(status_code: int, error_message: str, detail: str = None) -> Dict[str, Any]:
    """エラーレスポンスを作成"""
    error_body = {
        'success': False,
        'error': error_message
    }
    if detail:
        error_body['detail'] = detail
    
    return create_response(status_code, error_body)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda関数のメインハンドラー"""
    
    logger.info(f"Lambda関数が呼び出されました: {event}")
    
    try:
        # Q&Aシステムの初期化
        initialize_qa_system()
        
        # HTTPメソッドを確認
        http_method = event.get('httpMethod', '')
        
        # OPTIONSメソッド（CORS preflight）の処理
        if http_method == 'OPTIONS':
            return create_response(200, {'message': 'OK'})
        
        # POSTメソッドのみ許可
        if http_method != 'POST':
            return create_error_response(405, 'Method Not Allowed')
        
        # リクエストボディの解析
        try:
            if event.get('body'):
                body = json.loads(event['body'])
            else:
                return create_error_response(400, 'リクエストボディが必要です')
        except json.JSONDecodeError:
            return create_error_response(400, '無効なJSON形式です')
        
        # 質問の取得
        question = body.get('question', '').strip()
        if not question:
            return create_error_response(400, '質問が空です')
        
        # max_resultsパラメータの取得（デフォルト: 3）
        max_results = body.get('max_results', 3)
        if not isinstance(max_results, int) or max_results < 1 or max_results > 10:
            max_results = 3
        
        logger.info(f"質問を受信: {question}")
        
        # Q&Aシステムで回答を生成
        logger.info(f"質問処理を開始: {question}")
        result = qa_system.ask_question(question)
        
        if not result or not result.get('answer'):
            logger.error("回答生成に失敗しました")
            return create_error_response(500, '回答の生成に失敗しました')
        
        # 成功レスポンスを作成
        response_body = {
            'success': True,
            'answer': result['answer'],
            'confidence': result['confidence'],
            'sources': result['sources']
        }
        
        logger.info(f"回答を生成: 信頼度={result['confidence']:.3f}, ソース数={len(result['sources'])}")
        
        return create_response(200, response_body)
        
    except Exception as e:
        logger.error(f"Lambda実行中にエラーが発生: {e}")
        logger.error(traceback.format_exc())
        
        return create_error_response(500, 'サーバー内部エラー', str(e))

# ローカルテスト用
if __name__ == "__main__":
    # テスト用のイベントデータ
    test_event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'question': 'サイト内検索について教えて',
            'max_results': 3
        })
    }
    
    # Lambda関数を実行
    response = lambda_handler(test_event, None)
    print(json.dumps(response, ensure_ascii=False, indent=2))