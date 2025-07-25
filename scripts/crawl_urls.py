#!/usr/bin/env python3
"""
CSVファイルからURLを読み取り、各URLの内容をHTMLファイルとして保存するスクリプト
"""

import csv
import os
import time
import requests
from urllib.parse import urlparse, unquote
import re
from pathlib import Path
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class URLCrawler:
    def __init__(self, csv_file_path, output_dir="crawled_html", delay=1):
        """
        Args:
            csv_file_path: CSVファイルのパス
            output_dir: HTMLファイルの保存先ディレクトリ
            delay: リクエスト間の待機時間（秒）
        """
        self.csv_file_path = csv_file_path
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.session = requests.Session()
        
        # User-Agentを設定してブロックされにくくする
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 出力ディレクトリを作成
        self.output_dir.mkdir(exist_ok=True)
        
    def sanitize_filename(self, url):
        """URLから安全なファイル名を生成"""
        # URLをパースしてパスを取得
        parsed_url = urlparse(url)
        
        # パスとクエリパラメータを結合
        path_part = parsed_url.path + (f"?{parsed_url.query}" if parsed_url.query else "")
        
        # URLデコード
        path_part = unquote(path_part)
        
        # 安全でない文字を置換
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', path_part)
        safe_filename = re.sub(r'[^\w\-_.]', '_', safe_filename)
        safe_filename = re.sub(r'_+', '_', safe_filename)  # 連続するアンダースコアを1つに
        
        # ファイル名が長すぎる場合は短縮
        if len(safe_filename) > 200:
            safe_filename = safe_filename[:200]
        
        # 空の場合やドットで始まる場合の対処
        if not safe_filename or safe_filename.startswith('.'):
            safe_filename = f"page_{hash(url) % 10000}"
            
        return f"{safe_filename}.html"
    
    def fetch_url(self, url):
        """URLからHTMLコンテンツを取得"""
        try:
            logger.info(f"Fetching: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # 文字エンコーディングを適切に処理
            if response.encoding is None:
                response.encoding = 'utf-8'
            
            return response.text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def save_html(self, html_content, filename, url):
        """HTMLコンテンツをファイルに保存"""
        file_path = self.output_dir / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # HTMLにメタデータコメントを追加
                metadata_comment = f"<!-- Original URL: {url} -->\n<!-- Crawled at: {time.strftime('%Y-%m-%d %H:%M:%S')} -->\n"
                f.write(metadata_comment + html_content)
            
            logger.info(f"Saved: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving {filename}: {e}")
            return False
    
    def read_urls_from_csv(self):
        """CSVファイルからURLを読み取り"""
        urls = []
        
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as f:
                # CSVの最初の行をチェック
                first_line = f.readline().strip()
                f.seek(0)  # ファイルの先頭に戻る
                
                # ヘッダーがあるかチェック
                has_header = first_line.lower() in ['url', 'urls', 'link', 'links']
                
                reader = csv.reader(f)
                
                # ヘッダーをスキップ
                if has_header:
                    next(reader)
                
                for row in reader:
                    if row and row[0].strip():  # 空行でない場合
                        url = row[0].strip()
                        if url.startswith('http'):  # URLらしいもののみ
                            urls.append(url)
            
            logger.info(f"Found {len(urls)} URLs in CSV file")
            return urls
            
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            return []
    
    def crawl_all(self):
        """すべてのURLをクローリング"""
        urls = self.read_urls_from_csv()
        
        if not urls:
            logger.error("No URLs found in CSV file")
            return
        
        success_count = 0
        total_count = len(urls)
        
        for i, url in enumerate(urls, 1):
            logger.info(f"Processing {i}/{total_count}: {url}")
            
            # HTMLコンテンツを取得
            html_content = self.fetch_url(url)
            
            if html_content:
                # ファイル名を生成
                filename = self.sanitize_filename(url)
                
                # 重複ファイル名の処理
                counter = 1
                original_filename = filename
                while (self.output_dir / filename).exists():
                    name, ext = os.path.splitext(original_filename)
                    filename = f"{name}_{counter}{ext}"
                    counter += 1
                
                # HTMLファイルとして保存
                if self.save_html(html_content, filename, url):
                    success_count += 1
            
            # レート制限のための待機
            if i < total_count:  # 最後のリクエストの後は待機しない
                time.sleep(self.delay)
        
        logger.info(f"Crawling completed: {success_count}/{total_count} URLs successfully processed")
        logger.info(f"HTML files saved in: {self.output_dir.absolute()}")

def main():
    # 設定
    csv_file = "srcfile/helppage.csv"
    output_directory = "crawled_html"
    request_delay = 2  # リクエスト間隔（秒）
    
    # クローラーを初期化して実行
    crawler = URLCrawler(csv_file, output_directory, request_delay)
    crawler.crawl_all()

if __name__ == "__main__":
    main()