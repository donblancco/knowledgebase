# AWS Bedrock Knowledge Base - Terraform Configuration

このディレクトリには、AWS Bedrock Knowledge Baseの環境を構築するためのTerraformコードが含まれています。

## 構成要素

- **Knowledge Base**: AWS Bedrock Knowledge Base本体
- **S3 Bucket**: データソース用のS3バケット + Web配信用バケット
- **CloudFront**: CDNによる高速Web配信
- **Lambda@Edge**: Basic認証機能
- **OpenSearch Serverless**: ベクトルデータベース
- **Lambda + API Gateway**: Claude 3.5 Sonnet API
- **IAM Role/Policy**: 必要な権限設定
- **Data Source**: S3データソースの設定

## 事前準備

1. **Terraformのインストール**
   ```bash
   # macOS
   brew install terraform
   
   # または公式サイトからダウンロード
   ```

2. **AWS CLIの設定**
   ```bash
   aws configure
   ```

3. **Bedrockモデルアクセスの有効化**
   - AWS Consoleで以下のモデルへのアクセスを有効にする
   - Amazon Titan Embeddings G1 - Text
   - Claude 3.5 Sonnet v2 (回答生成用)

## デプロイ手順

1. **変数ファイルの準備**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # 必要に応じて値を編集
   ```

2. **Terraformの初期化**
   ```bash
   terraform init
   ```

3. **プランの確認**
   ```bash
   terraform plan
   ```

4. **インフラストラクチャの作成**
   ```bash
   terraform apply
   ```

5. **出力値の確認**
   ```bash
   terraform output
   ```

## 出力値

- `knowledge_base_id`: 作成されたKnowledge BaseのID
- `s3_bucket_name`: データ用S3バケット名
- `web_bucket_name`: Web配信用S3バケット名
- `cloudfront_domain_name`: CloudFrontドメイン名
- `web_interface_url`: WebインターフェースURL
- `api_gateway_url`: API Gateway URL
- `lambda_function_name`: Lambda関数名

## 環境変数の設定

Terraformのデプロイ後、以下の環境変数を設定してください：

```bash
# .envファイルに設定
KNOWLEDGE_BASE_ID=$(terraform output -raw knowledge_base_id)
AWS_REGION=us-east-1
```

## クリーンアップ

```bash
terraform destroy
```

## 注意事項

- OpenSearch Serverlessは最小構成でも費用が発生します
- データの同期には時間がかかる場合があります
- 初回実行時はBedrockモデルのアクセス許可が必要です

## トラブルシューティング

### よくある問題

1. **Bedrockモデルへのアクセス権限エラー**
   - AWS Console > Bedrock > Model accessで必要なモデルを有効にする

2. **OpenSearch Serverlessの制限**
   - リージョンごとの制限を確認する
   - アカウントの制限を確認する

3. **IAM権限エラー**
   - デプロイ用のIAMユーザーに十分な権限があることを確認する