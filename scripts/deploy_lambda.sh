#!/bin/bash

# Lambda関数デプロイスクリプト
# AWS Bedrock Knowledge Base Q&A APIのデプロイ

set -e

echo "Lambda関数のデプロイを開始します..."

# デプロイ用の一時ディレクトリを作成
TEMP_DIR=$(mktemp -d)
echo "一時ディレクトリ: $TEMP_DIR"

# 必要なファイルをコピー（新しいsrcディレクトリから）
cp src/lambda_handler.py "$TEMP_DIR/"
cp src/bedrock_qa_system.py "$TEMP_DIR/"

# .envファイルが存在する場合はコピー（オプション）
if [ -f ".env" ]; then
    echo ".envファイルをコピーしています..."
    cp .env "$TEMP_DIR/"
fi

# 依存関係をインストール
echo "依存関係をインストールしています..."
cd "$TEMP_DIR"

# requirements.txtの内容を一時ファイルに作成
cat > requirements.txt << EOF
boto3==1.34.144
botocore==1.34.144
python-dotenv==1.0.0
EOF

# 依存関係をインストール
pip install -r requirements.txt -t .

# デプロイパッケージを作成
echo "デプロイパッケージを作成しています..."
zip -r lambda_deployment.zip .

# パッケージを元のディレクトリに移動
mv lambda_deployment.zip ../

echo "Lambda関数のデプロイパッケージが作成されました: lambda_deployment.zip"

# 一時ディレクトリを削除
cd ..
rm -rf "$TEMP_DIR"

echo "Terraformを使用してインフラをデプロイしてください:"
echo "cd terraform"
echo "terraform init"
echo "terraform plan"
echo "terraform apply"

echo "デプロイが完了しました！"