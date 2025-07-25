# AWS Bedrock Knowledge Base 質問応答システム

このプロジェクトは、AWS Bedrock Knowledge Baseを使用した質問応答システムです。
CSVファイルから取得したURLをクローリングしてHTMLファイルを生成し、それをベースにした質問応答システムを構築します。

## システム構成

- **データソース**: 637個のクローリングされたHTMLファイル（S3に保存）
- **Knowledge Base**: AWS Bedrock Knowledge Base (`G4TRACKHQC`)
- **ベクトルDB**: OpenSearch Serverless
- **埋め込みモデル**: Amazon Titan Embeddings G1 - Text v1
- **回答生成モデル**: Claude 3.5 Sonnet v2 (Messages API)
- **バックエンド**: Lambda + API Gateway（`https://1d3k2lygvg.execute-api.us-east-1.amazonaws.com/dev`）
- **フロントエンド**: S3 + CloudFront（`https://d3ih2yfmynp13a.cloudfront.net`）
- **認証**: Lambda@Edge Basic認証

## セットアップ方法

### 1. 依存関係のインストール

```bash
# 仮想環境を作成
python3 -m venv kb_venv

# 仮想環境を有効化
source kb_venv/bin/activate

# 依存関係をインストール
pip install boto3 python-dotenv requests beautifulsoup4 lxml opensearch-py
```

### 2. 環境変数の設定

`.env.example`を`.env`にコピーして、必要な値を設定してください：

```bash
cp .env.example .env
```

設定が必要な項目：
```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
KNOWLEDGE_BASE_ID=G4TRACKHQC
BEDROCK_MODEL_ID=arn:aws:bedrock:us-east-1:279511116447:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0
```

### 3. AWS Bedrock モデルアクセスの有効化

AWS Bedrockコンソールで以下のモデルを有効化してください：
1. **Amazon Titan Embeddings G1 - Text** (埋め込み用)
2. **Claude 3.5 Sonnet** (回答生成用)

## データ準備

### CSVファイルからHTMLファイルの生成

```bash
# URLクローリングスクリプトを実行
python crawl_urls.py
```

これにより、`srcfile/helppage.csv`のURLから637個のHTMLファイルが`crawled_html/`ディレクトリに生成されます。

### S3へのアップロード

```bash
# S3バケットへHTMLファイルをアップロード
aws s3 sync crawled_html/ s3://bedrock-kb-qa-data-f501c9ff647296c6/html/
```

## 使用方法

### Webインターフェース（推奨）

**本番環境URL**: `https://d3ih2yfmynp13a.cloudfront.net`

**Basic認証情報**:
- ユーザー名: `[設定されたユーザー名]`
- パスワード: `[設定されたパスワード]`

**使用方法**:
1. 上記URLにアクセス
2. Basic認証ダイアログで認証情報を入力
3. 質問フォームに入力（例：「サイト内検索について教えて」）
4. Claude 3.5 Sonnetが生成した詳細な回答を確認

**ローカル開発**:
1. `examples/web_interface.html`をブラウザで開く
2. ローカルAPIサーバー（ポート8001）を起動して使用

### ローカル開発用APIサーバー

```bash
# ローカルAPIサーバーを起動
python local_api_server.py

# ブラウザでweb_interface.htmlを開いて使用
```

### コマンドラインから実行

```bash
# 仮想環境を有効化
source kb_venv/bin/activate

# 対話的Q&Aシステムを実行
python bedrock_qa_system.py
```

### プログラムから使用

```python
from bedrock_qa_system import BedrockKnowledgeBaseQA

qa_system = BedrockKnowledgeBaseQA()
result = qa_system.ask_question("サイト内検索について教えて")

print(f"回答: {result['answer']}")
print(f"信頼度: {result['confidence']:.3f}")
print(f"参考ソース: {len(result['sources'])}件")
```

### APIテスト

```bash
# cURLでAPIをテスト（Claude 3.5 Sonnet使用）
curl -X POST \
  https://1d3k2lygvg.execute-api.us-east-1.amazonaws.com/dev/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "サイト内検索について教えて", "max_results": 3}'
```

## ディレクトリ構造

```
bedrock/
├── src/                          # メインソースコード
│   ├── bedrock_qa_system.py     # Q&Aシステム（Claude 3.5 Sonnet対応）
│   └── lambda_handler.py        # AWS Lambda関数のハンドラー
├── examples/                     # 使用例・デモ
│   ├── web_interface.html       # Webユーザーインターフェース
│   ├── local_api_server.py      # ローカル開発用APIサーバー（ポート8001）
│   └── interactive_demo.py      # 対話型デモ
├── scripts/                      # 各種スクリプト
│   ├── crawl_urls.py            # URLクローリングスクリプト
│   ├── deploy_lambda.sh         # Lambda関数デプロイスクリプト
│   └── create_kb_auto.py        # Knowledge Base自動作成
├── tests/                        # テストファイル
│   ├── test_qa.py               # Q&Aシステムテスト
│   └── test_api.py              # APIテスト
├── config/                       # 設定ファイル
│   ├── bedrock_policy.json      # IAMポリシー
│   └── update_access_policy.json # アクセスポリシー更新
├── docs/                         # ドキュメント
│   ├── .claude/CLAUDE.md        # プロジェクト詳細仕様
│   └── API_USAGE.md             # API使用方法
├── terraform/                    # インフラ構築用Terraformファイル
│   ├── main.tf                  # メインリソース
│   ├── web_hosting.tf           # S3+CloudFront設定
│   ├── lambda_edge_auth.tf      # Basic認証Lambda@Edge
│   └── outputs.tf               # 出力定義
├── srcfile/                      # データファイル
│   └── helppage.csv             # クローリング対象のURL一覧
└── crawled_html/                 # クローリング済みHTMLファイル（637件）
```

## 機能

- **Knowledge Baseからの関連情報検索**: 質問に関連する情報を自動検索（637件のHTMLファイル + Confluence）
- **Claude 3.5 Sonnet回答生成**: Messages API使用で自然で詳細な日本語回答
- **信頼度スコアの表示**: 回答の信頼度を数値で表示（通常0.7以上）
- **参考ソースの提供**: 回答の根拠となったソースURLを表示
- **S3+CloudFront配信**: 高速・高可用性Webインターフェース
- **Basic認証**: Lambda@Edgeによるエッジレベル認証
- **重複排除機能**: コンテンツハッシュと記事IDによる重複排除
- **レスポンシブデザイン**: モバイル対応の美しいUI（#40b87c背景）
- **高度な回答フォーマット**: 自動改行・Markdown変換で読みやすい回答表示
- **多言語対応**: 日本語・英語混在データから日本語で回答

## 必要な権限

IAMユーザーには以下の権限が必要です：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:*",
        "bedrock-runtime:*",
        "bedrock-agent:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "aoss:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::bedrock-kb-qa-data-*",
        "arn:aws:s3:::bedrock-kb-qa-data-*/*"
      ]
    }
  ]
}
```

## 実行例

### API レスポンス例

```json
{
  "success": true,
  "answer": "サイト内検索では、翻訳ページも検索対象となります。ただし、検索エンジンで上位に表示されるためには、現地の言葉で適切に翻訳したり、コンテンツを拡充させたりするなどのSEO対策が必要です。",
  "confidence": 0.73191357,
  "sources": [
    {
      "uri": "s3://bedrock-kb-qa-data-f501c9ff647296c6/html/_hc_ja_articles_360009100212-multilingual-search-guide_.html",
      "score": 0.73191357
    },
    {
      "uri": "s3://bedrock-kb-qa-data-f501c9ff647296c6/html/_hc_ja_articles_360015255831-スマホサイトにも対応していますか_.html",
      "score": 0.72106814
    }
  ]
}
```

### コマンドライン実行例

```bash
$ python bedrock_qa_system.py

質問を入力してください (終了するには 'quit' と入力): サイト内検索について教えて

回答: サイト内検索では、翻訳ページも検索対象となります...
信頼度: 0.732
参考ソース:
  - _hc_ja_articles_360009100212-multilingual-search-guide_.html (スコア: 0.732)
```

## インフラ構築

Terraformを使用してインフラを自動構築する場合：

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

**作成されるリソース**:
- S3バケット（データ保存・Web配信）
- CloudFrontディストリビューション（CDN）
- Lambda@Edge関数（Basic認証）
- Knowledge Base + OpenSearch Serverless
- Lambda関数（API）+ API Gateway
- IAMロール・ポリシー

詳細は[terraform/README.md](terraform/README.md)を参照してください。

## 回答フォーマット機能

### 自動フォーマット処理

システムは以下の自動フォーマット機能を提供します：

1. **Markdown変換**:
   - `**太字**` → `<strong>太字</strong>`
   - `## 見出し` → `<h3>見出し</h3>`

2. **改行最適化**:
   - 句点（。）後の適切な改行挿入
   - 長文の自動分割（100文字以上）
   - 見出し・リスト項目の前後改行

3. **HTML変換**:
   - `\n\n` → `<br><br>` (段落間)
   - `\n` → `<br>` (単一改行)

### 実装詳細

```python
# format_answer関数の主要機能
def format_answer(self, answer: str) -> str:
    # 1. 見出し処理
    formatted = re.sub(r'##\s+([^\n]+)', r'<h3>\1</h3>', formatted)
    
    # 2. 太字処理
    formatted = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', formatted)
    
    # 3. 改行最適化
    formatted = re.sub(r'。\s*(?=[あ-んア-ン一-龯]*)', '。\n\n', formatted)
    
    # 4. HTML変換
    formatted = formatted.replace('\n\n', '<br><br>')
    formatted = formatted.replace('\n', '<br>')
```

## トラブルシューティング

### よくある問題

1. **モデルアクセスエラー**: AWS Bedrockコンソールでモデルアクセスを有効化してください
2. **OpenSearchアクセス権限エラー**: IAMポリシーにOpenSearch権限を追加してください
3. **トークン制限エラー**: コンテキストの長さを調整してください
4. **フォーマットエラー**: 回答が正しく表示されない場合は、HTMLタグの変換処理を確認してください

### ログ確認

```bash
# 詳細なログを確認
python bedrock_qa_system.py --verbose
```

## 貢献

プルリクエストやイシューの報告を歓迎します。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
