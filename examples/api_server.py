#!/usr/bin/env python3
"""
AWS Bedrock Knowledge Base Q&A API Server
FastAPIを使用したREST API
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import traceback
import uvicorn
from bedrock_qa_system import BedrockKnowledgeBaseQA

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="AWS Bedrock Knowledge Base Q&A API",
    description="AWS Bedrock Knowledge Baseを使用した質問応答API",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# リクエストモデル
class QuestionRequest(BaseModel):
    question: str
    max_results: Optional[int] = 3

class QuestionResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    success: bool = True

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    success: bool = False

# グローバルなQ&Aシステムインスタンス
qa_system = None

@app.on_event("startup")
async def startup_event():
    """アプリケーション開始時にQ&Aシステムを初期化"""
    global qa_system
    try:
        qa_system = BedrockKnowledgeBaseQA()
        logger.info("Q&Aシステムが正常に初期化されました")
    except Exception as e:
        logger.error(f"Q&Aシステムの初期化に失敗: {e}")
        raise

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "AWS Bedrock Knowledge Base Q&A API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "qa_system_ready": qa_system is not None
    }

@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """質問に回答するエンドポイント"""
    try:
        if qa_system is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Q&Aシステムが初期化されていません"
            )
        
        if not request.question.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="質問が空です"
            )
        
        logger.info(f"質問を受信: {request.question}")
        
        # Q&Aシステムで回答を生成
        result = qa_system.ask_question(request.question)
        
        response = QuestionResponse(
            answer=result['answer'],
            confidence=result['confidence'],
            sources=result['sources']
        )
        
        logger.info(f"回答を生成: 信頼度={result['confidence']:.3f}, ソース数={len(result['sources'])}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"質問処理中にエラーが発生: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"内部サーバーエラー: {str(e)}"
        )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """グローバル例外ハンドラー"""
    logger.error(f"予期しないエラーが発生: {exc}")
    logger.error(traceback.format_exc())
    
    return ErrorResponse(
        error="内部サーバーエラー",
        detail=str(exc)
    )

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )