#!/usr/bin/env python3
"""
ローカル開発用のAPIサーバー
Webインターフェースとの連携テスト用
"""

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import traceback
from bedrock_qa_system import BedrockKnowledgeBaseQA

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIHandler(BaseHTTPRequestHandler):
    """API リクエストハンドラー"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def do_OPTIONS(self):
        """CORS preflight リクエストの処理"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def do_POST(self):
        """POST リクエストの処理"""
        try:
            parsed_path = urlparse(self.path)
            
            if parsed_path.path == '/ask':
                self.handle_ask_question()
            else:
                self.send_error_response(404, "エンドポイントが見つかりません")
                
        except Exception as e:
            logger.error(f"POST処理中にエラーが発生: {e}")
            logger.error(traceback.format_exc())
            self.send_error_response(500, "内部サーバーエラー")
    
    def handle_ask_question(self):
        """質問処理エンドポイント"""
        try:
            # リクエストボディを取得
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # JSONをパース
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_error_response(400, "無効なJSON形式です")
                return
            
            # 質問を取得
            question = data.get('question', '').strip()
            if not question:
                self.send_error_response(400, "質問が空です")
                return
            
            logger.info(f"質問を受信: {question}")
            
            # Q&Aシステムで回答を生成
            if not hasattr(self.server, 'qa_system'):
                self.server.qa_system = BedrockKnowledgeBaseQA()
                logger.info("Q&Aシステムを初期化しました")
            
            result = self.server.qa_system.ask_question(question)
            
            # 成功レスポンスを返す
            response_data = {
                'success': True,
                'answer': result['answer'],
                'confidence': result['confidence'],
                'sources': result['sources']
            }
            
            self.send_json_response(200, response_data)
            logger.info(f"回答を生成: 信頼度={result['confidence']:.3f}")
            
        except Exception as e:
            logger.error(f"質問処理中にエラーが発生: {e}")
            logger.error(traceback.format_exc())
            self.send_error_response(500, "質問処理に失敗しました")
    
    def send_json_response(self, status_code, data):
        """JSON レスポンスを送信"""
        self.send_response(status_code)
        self.send_cors_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        
        response_json = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response_json.encode('utf-8'))
    
    def send_error_response(self, status_code, error_message):
        """エラーレスポンスを送信"""
        error_data = {
            'success': False,
            'error': error_message
        }
        self.send_json_response(status_code, error_data)
    
    def send_cors_headers(self):
        """CORS ヘッダーを送信"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')
    
    def log_message(self, format, *args):
        """ログメッセージをカスタマイズ"""
        logger.info(f"{self.address_string()} - {format % args}")

def run_server(port=8001):
    """APIサーバーを起動"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, APIHandler)
    
    logger.info(f"ローカルAPIサーバーを起動中... http://localhost:{port}")
    logger.info("終了するには Ctrl+C を押してください")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("サーバーを停止中...")
        httpd.server_close()
        logger.info("サーバーが停止しました")

if __name__ == '__main__':
    run_server()