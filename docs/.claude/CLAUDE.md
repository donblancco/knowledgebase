# AWS Bedrock Knowledge Base Q&A システム

このプロジェクトは、AWS Bedrock Knowledge Baseを使用したWOVN.ioヘルプページの質問応答システムです。

## プロジェクト概要

- **データソース**: 637個のクローリングされたHTMLファイル（S3保存）
- **Knowledge Base**: AWS Bedrock Knowledge Base (`G4TRACKHQC`)
- **ベクトルDB**: OpenSearch Serverless  
- **埋め込みモデル**: Amazon Titan Embeddings G1 - Text v1
- **回答生成モデル**: Claude 3.5 Sonnet v2 (Messages API)
- **バックエンド**: Lambda関数 `bedrock-kb-qa-qa-api` + API Gateway
- **フロントエンド**: S3 + CloudFront + Lambda@Edge Basic認証

## アーキテクチャ

```
Web Interface (https://d3ih2yfmynp13a.cloudfront.net)
       ↓
CloudFront + Lambda@Edge (Basic認証: wovn-admin/WPv6sVYE)
       ↓  
S3 (web_interface.html) ←→ API Gateway (https://1d3k2lygvg.execute-api.us-east-1.amazonaws.com/dev)
                              ↓
                         Lambda Function (bedrock-kb-qa-qa-api) 
                              ↓
                         Bedrock Knowledge Base (G4TRACKHQC) → OpenSearch Serverless
                              ↓
                         Bedrock LLM (Claude 3.5 Sonnet v2 - Messages API)
```

## ファイル構成

### メインファイル
- `src/bedrock_qa_system.py` - Q&Aシステムのコア機能
- `src/lambda_handler.py` - AWS Lambda関数のハンドラー
- `examples/web_interface.html` - Webユーザーインターフェース
- `examples/local_api_server.py` - ローカル開発用APIサーバー

### テスト・デモファイル
- `tests/test_*.json` - システムのテストファイル群
- `examples/interactive_demo.py` - 対話型デモスクリプト

### データファイル
- `data/crawled_html/` - クローリングされたHTMLファイル（637件）
- `data/srcfile/helppage.csv` - クローリング対象のURL一覧

### 設定・デプロイファイル
- `.env.example` - 環境変数の設定例
- `requirements.txt` - Python依存関係
- `scripts/deploy_lambda.sh` - Lambda デプロイスクリプト
- `terraform/` - インフラ構築用Terraformファイル
- `config/` - 各種設定ファイル
- `build/` - ビルド成果物（zipファイル等）

## セットアップ

### 1. 環境変数設定
```bash
cp .env.example .env
# .envファイルを編集してAWS認証情報を設定
```

### 2. 仮想環境とパッケージインストール
```bash
python3 -m venv kb_venv
source kb_venv/bin/activate
pip install -r requirements.txt
```

### 3. ローカル開発
```bash
# APIサーバーを起動（ポート8001）
python examples/local_api_server.py

# Webインターフェースを開く
open examples/web_interface.html
```

### 4. 本番環境での使用
- **Web Interface URL**: `https://d3ih2yfmynp13a.cloudfront.net`
- **Basic認証**: ユーザー名 `wovn-admin` / パスワード `WPv6sVYE`
- **API Gateway URL**: `https://1d3k2lygvg.execute-api.us-east-1.amazonaws.com/dev`
- **Lambda関数名**: `bedrock-kb-qa-qa-api`
- **Knowledge Base ID**: `G4TRACKHQC`

## API仕様

### エンドポイント
- `POST /ask` - 質問を投稿して回答を取得

### リクエスト例
```json
{
  "question": "WOVN.ioのサイト内検索について教えて",
  "max_results": 3
}
```

### レスポンス例
```json
{
  "success": true,
  "answer": "WOVN.ioのサイト内検索は、翻訳ページも検索対象となります。ただし、検索エンジンで上位に表示されるためには、現地の言葉で適切に翻訳したり、コンテンツを拡充させたりするなどのSEO対策が必要です。",
  "confidence": 0.73191357,
  "sources": [
    {
      "uri": "s3://bedrock-kb-qa-data-f501c9ff647296c6/html/_hc_ja_articles_360009100212-WOVN-導入後-外国語で検索にヒットさせるには_.html",
      "score": 0.73191357
    },
    {
      "uri": "s3://bedrock-kb-qa-data-f501c9ff647296c6/html/_hc_ja_articles_360015255831-スマホサイトにも対応していますか_.html",
      "score": 0.72106814
    }
  ]
}
```

## デプロイ方法

### Lambda関数デプロイ
```bash
# デプロイパッケージ作成
zip -r build/lambda_deployment.zip src/bedrock_qa_system.py src/lambda_handler.py

# 既存Lambda関数の更新
aws lambda update-function-code \
  --function-name bedrock-kb-qa-qa-api \
  --region us-east-1 \
  --zip-file fileb://build/lambda_deployment.zip

# 環境変数の設定（Claude 3.5 Sonnet v2 推論プロファイル使用）
aws lambda update-function-configuration \
  --function-name bedrock-kb-qa-qa-api \
  --region us-east-1 \
  --environment Variables='{KNOWLEDGE_BASE_ID=G4TRACKHQC,BEDROCK_MODEL_ID=arn:aws:bedrock:us-east-1:279511116447:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0}'
```

### Terraform使用
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## 使用方法

### コマンドライン
```bash
python src/bedrock_qa_system.py
```

### プログラム内で使用
```python
from src.bedrock_qa_system import BedrockKnowledgeBaseQA

qa_system = BedrockKnowledgeBaseQA()
result = qa_system.ask_question("質問内容")
print(result['answer'])
```

### Web インターフェース
1. `examples/web_interface.html` をブラウザで開く
2. 質問フォームに入力（例：「WOVN.ioのサイト内検索について教えて」）
3. AIが生成した回答と参考ソースを確認
4. 背景色は #40b87c のグラデーション

## 機能

- ✅ Knowledge Base (G4TRACKHQC) からの関連情報検索（637件のHTMLファイル）
- ✅ Bedrock LLM (Claude 3.5 Sonnet v2) Messages API使用した詳細回答生成
- ✅ 信頼度スコアの表示（通常0.7以上）
- ✅ 参考ソースの提供（S3 URIとスコア）
- ✅ 重複排除機能（コンテンツハッシュと記事ID）
- ✅ S3+CloudFront高速Webインターフェース配信
- ✅ Lambda@Edge Basic認証（wovn-admin/WPv6sVYE）
- ✅ CORS対応API（本番環境Lambda + API Gateway）
- ✅ エラーハンドリングとログ出力
- ✅ ローカル/Lambda環境自動判定
- ✅ IAMロール認証対応
- ✅ レスポンシブデザイン（#40b87c背景）
- ✅ 参考ソースの種類別表示（色分けバッジ）
- ✅ 複数データソース対応（ヘルプページ・技術ドキュメント・Confluence）

## 参考ソースの種類と分類

### データソース構成
- **ヘルプページ** (緑色バッジ): WOVN.ioの公式ヘルプページ（637件）
- **WOVN.io Technical Document** (青色バッジ): 技術ドキュメント（S3保存）
- **Confluence** (オレンジ色バッジ): 社内ドキュメント・Wiki（Confluenceコネクタ）

### 参考ソース表示機能
- **URIパス解析**: S3 URIやConfluenceコネクタの情報を適切なWOVN.ioサイトURLに変換
- **色分け表示**: 各データソースを視覚的に区別
- **リンク機能**: 参考ソースから元のドキュメントへ直接アクセス可能

### URL変換ルール
- **helppage/** → `https://support.wovn.io/hc/`
- **technical_docs/** → `https://docs.wovn.io/`
- **Confluence** → `https://wovnio.atlassian.net/wiki/spaces/wovnio/`

### Confluenceから情報を取得する質問例

**社内プロセス関連**:
- "meeting notes and decisions"
- "internal documentation"
- "team processes"
- "project updates"

**組織・チーム関連**:
- "team guidelines"
- "department processes"
- "company meetings"
- "internal communications"

**開発・企画関連**:
- "development roadmap"
- "feature planning"
- "sprint planning"
- "project documentation"

## トラブルシューティング

### よくある問題と解決方法
1. **モデルアクセスエラー**: AWS Bedrockコンソールでモデルアクセスを有効化
2. **Lambda権限エラー**: IAMロールに適切なBedrock権限を追加
3. **Knowledge Base検索エラー**: Knowledge Base ID (G4TRACKHQC) が正しいか確認
4. **API接続エラー**: 
   - ローカル: `python examples/local_api_server.py` でサーバー起動確認
   - 本番: API Gateway URL が正しいか確認
5. **dotenv ImportError**: Lambda環境では不要、try-except で対応済み

### ログ確認
```bash
# ローカル実行時の詳細ログ
python src/bedrock_qa_system.py

# Lambda関数のログ確認
aws logs get-log-events \
  --log-group-name "/aws/lambda/bedrock-kb-qa-qa-api" \
  --region us-east-1

# リアルタイムログ確認
aws logs tail /aws/lambda/bedrock-kb-qa-qa-api --region us-east-1 --follow
```

## 必要な権限

IAMユーザーには以下の権限が必要:
- `bedrock:*`
- `bedrock-runtime:*`
- `bedrock-agent:*`
- `aoss:*`
- `s3:GetObject`, `s3:ListBucket`, `s3:PutObject`

## パフォーマンス

- **平均レスポンス時間**: 2-6秒（Knowledge Base検索 + LLM生成）
- **信頼度スコア**: 通常0.7以上（実測値: 0.732）
- **データ取得率**: 637件中から関連情報を検索
- **同時接続**: Lambda関数により自動スケール
- **API可用性**: 99.9%以上（AWS SLA）

## 現在の動作状況

✅ **Knowledge Base**: G4TRACKHQC (ACTIVE)  
✅ **データソース**: wovn-helppage (AVAILABLE, 637件)  
✅ **Lambda関数**: bedrock-kb-qa-qa-api (Claude 3.5 Sonnet v2対応)  
✅ **API Gateway**: https://1d3k2lygvg.execute-api.us-east-1.amazonaws.com/dev  
✅ **Web Interface**: https://d3ih2yfmynp13a.cloudfront.net  
✅ **Basic認証**: wovn-admin/WPv6sVYE  
✅ **最新テスト**: 2025-07-10 Claude 3.5 Sonnet正常応答確認済み

## ライセンス

MIT License