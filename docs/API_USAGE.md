# AWS Bedrock Knowledge Base Q&A API 使用ガイド

## 概要

このAPIは、AWS Bedrock Knowledge Baseを使用した質問応答システムです。Lambda + API Gatewayを使用してサーバーレスで実装されています。

**主な機能**:
- Claude 3.5 Sonnet による高品質な日本語回答
- 多言語化 Knowledge Base（637件のHTMLファイル + Confluence）からの情報検索
- 自動フォーマット機能（Markdown→HTML変換、改行最適化）
- 多言語対応（日本語・英語混在データから日本語で回答）

## エンドポイント

### POST /ask

質問に対する回答を生成します。

#### リクエスト

```json
{
  "question": "質問内容",
  "max_results": 3
}
```

#### パラメータ

- `question` (required): 質問内容（文字列）
- `max_results` (optional): 検索結果の最大数（1-10、デフォルト: 3）

#### レスポンス

##### 成功時（200 OK）

```json
{
  "success": true,
  "answer": "回答内容（HTML形式で自動フォーマット済み）",
  "confidence": 0.85,
  "sources": [
    {
      "uri": "s3://bucket/path/to/file.html",
      "score": 0.92,
      "excerpt": "関連するテキストの抜粋"
    }
  ]
}
```

**回答フォーマット機能**:
- **Markdown変換**: `**太字**` → `<strong>太字</strong>`、`## 見出し` → `<h3>見出し</h3>`
- **改行最適化**: 句点後の適切な改行挿入、長文の自動分割
- **HTML変換**: `\n\n` → `<br><br>`、`\n` → `<br>`

##### エラー時（400 Bad Request）

```json
{
  "success": false,
  "error": "質問が空です"
}
```

##### エラー時（500 Internal Server Error）

```json
{
  "success": false,
  "error": "サーバー内部エラー",
  "detail": "詳細なエラーメッセージ"
}
```

## 使用例

### curl

```bash
curl -X POST https://your-api-gateway-url/dev/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "サイト内検索について教えて",
    "max_results": 3
  }'
```

### Python

```python
import requests
import json

url = "https://your-api-gateway-url/dev/ask"
payload = {
    "question": "サイト内検索について教えて",
    "max_results": 3
}

response = requests.post(url, json=payload)
result = response.json()

if result['success']:
    print(f"回答: {result['answer']}")
    print(f"信頼度: {result['confidence']:.3f}")
    print(f"参考ソース: {len(result['sources'])}件")
else:
    print(f"エラー: {result['error']}")
```

### JavaScript

```javascript
const url = "https://your-api-gateway-url/dev/ask";
const payload = {
    question: "サイト内検索について教えて",
    max_results: 3
};

fetch(url, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload)
})
.then(response => response.json())
.then(result => {
    if (result.success) {
        console.log(`回答: ${result.answer}`);
        console.log(`信頼度: ${result.confidence.toFixed(3)}`);
        console.log(`参考ソース: ${result.sources.length}件`);
    } else {
        console.log(`エラー: ${result.error}`);
    }
});
```

## デプロイ方法

### 1. Lambda関数のデプロイパッケージ作成

```bash
./deploy_lambda.sh
```

### 2. Terraformでインフラをデプロイ

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### 3. API URLの確認

```bash
terraform output api_gateway_url
```

## テスト方法

### ローカルテスト

```bash
python test_api.py
```

### APIテスト

```bash
python lambda_handler.py
```

## エラーハンドリング

### 一般的なエラー

- **400 Bad Request**: リクエストの形式が不正
- **405 Method Not Allowed**: POSTメソッド以外でのアクセス
- **500 Internal Server Error**: サーバー内部エラー

### トラブルシューティング

1. **Lambda関数が初期化されない**
   - 環境変数の設定を確認
   - IAM権限を確認

2. **Knowledge Baseにアクセスできない**
   - Knowledge Base IDが正しいか確認
   - Bedrock権限が付与されているか確認

3. **タイムアウトエラー**
   - Lambda関数のタイムアウト設定を確認
   - Knowledge Baseの応答時間を確認

## 制限事項

- Lambda関数のタイムアウト: 30秒
- メモリ: 512MB
- リクエストボディサイズ: 6MB以下
- Knowledge Base検索結果: 最大10件

## セキュリティ

- API GatewayはCORS設定済み
- 認証は設定されていません（必要に応じて追加）
- HTTPSでの通信を推奨