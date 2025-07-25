import boto3
import json
import os
from typing import Dict, Any, List
import logging
import re

# ローカル環境でのみdotenvを読み込み
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Lambda環境ではdotenvが不要
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BedrockKnowledgeBaseQA:
    def __init__(self):
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.knowledge_base_id = os.getenv('KNOWLEDGE_BASE_ID')
        self.model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
        
        # 簡単なクエリキャッシュ（同じ質問の連続実行を防ぐ）
        self._query_cache = {}
        self._cache_max_size = 10
        
        # Lambda環境ではIAMロールを使用、ローカルでは認証情報を使用
        if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            # Lambda環境: IAMロールを使用
            self.bedrock_agent_runtime = boto3.client(
                'bedrock-agent-runtime',
                region_name=self.aws_region
            )
            
            self.bedrock_runtime = boto3.client(
                'bedrock-runtime',
                region_name=self.aws_region
            )
        else:
            # ローカル環境: 認証情報を使用
            self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
            self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            
            self.bedrock_agent_runtime = boto3.client(
                'bedrock-agent-runtime',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
            
            self.bedrock_runtime = boto3.client(
                'bedrock-runtime',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
    
    def translate_query_to_english(self, query: str) -> str:
        """日本語クエリを英語に翻訳"""
        # 一般的な日本語-英語技術用語マッピング
        translation_map = {
            'クローラー': 'crawler',
            'クローラートリガー': 'crawler trigger',
            'ウィジェット': 'widget',
            'ウィジェット設定': 'widget settings',
            'プロキシ': 'proxy',
            'プロキシ設定': 'proxy settings',
            'トリガー': 'trigger',
            'アクティベーター': 'activator',
            'アクティベータ': 'activator',
            'API': 'API',
            'SDK': 'SDK',
            'ライブラリ': 'library',
            'ライブラリー': 'library',
            'フレームワーク': 'framework',
            'プラグイン': 'plugin',
            'コンフィグ': 'config',
            '設定': 'settings',
            '機能': 'feature',
            'ドキュメント': 'documentation',
            'ドキュメンテーション': 'documentation',
            'サポート': 'support',
            'デバッグ': 'debug',
            'エラー': 'error',
            'ログ': 'log',
            'ログイン': 'login',
            'ユーザー': 'user',
            'アカウント': 'account',
            'プロジェクト': 'project',
            'ダッシュボード': 'dashboard',
            'レポート': 'report',
            'レポーティング': 'reporting',
            'インテグレーション': 'integration',
            'セットアップ': 'setup',
            'インストール': 'install',
            'コンフィギュレーション': 'configuration',
            'カスタマイズ': 'customize',
            'カスタマイゼーション': 'customization'
        }
        
        # 完全一致での変換
        if query in translation_map:
            return translation_map[query]
        
        # 部分一致での変換（大文字小文字を区別しない）
        translated_query = query
        for jp_term, en_term in translation_map.items():
            if jp_term in query:
                translated_query = translated_query.replace(jp_term, en_term)
        
        # 英語単語の検出と処理
        import re
        # 「Activator」「Widget」などの英語単語を検出
        english_words = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', query)
        for word in english_words:
            if word.lower() not in translated_query.lower():
                translated_query += f" {word.lower()}"
        
        return translated_query

    def retrieve_from_knowledge_base(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Knowledge Baseから関連情報を取得（多言語検索対応・重複排除機能付き）"""
        import time
        
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # 多言語検索：元のクエリと英語翻訳版の両方で検索
                all_results = []
                
                # 1. 元のクエリで検索
                response_original = self.bedrock_agent_runtime.retrieve(
                    knowledgeBaseId=self.knowledge_base_id,
                    retrievalQuery={
                        'text': query
                    },
                    retrievalConfiguration={
                        'vectorSearchConfiguration': {
                            'numberOfResults': max_results * 2
                        }
                    }
                )
                all_results.extend(response_original.get('retrievalResults', []))
                
                # 2. 英語翻訳版で検索（元のクエリと異なる場合のみ）
                english_query = self.translate_query_to_english(query)
                if english_query != query:
                    logger.info(f"英語翻訳クエリで追加検索: '{query}' → '{english_query}'")
                    response_english = self.bedrock_agent_runtime.retrieve(
                        knowledgeBaseId=self.knowledge_base_id,
                        retrievalQuery={
                            'text': english_query
                        },
                        retrievalConfiguration={
                            'vectorSearchConfiguration': {
                                'numberOfResults': max_results * 2
                            }
                        }
                    )
                    all_results.extend(response_english.get('retrievalResults', []))
                
                # 結果をマージ
                response = {'retrievalResults': all_results}
                
                results = []
                seen_content = set()
                seen_articles = set()
                
                # データソース優先順位の定義とスコアボーナス
                data_source_priority = {
                    '9JIZ7NR5GM': 1,  # technical-docs (最高優先度)
                    'BCI4SYCYPF': 2,  # confluence-docs
                    'VO92FYFPG6': 3   # helppage (最低優先度)
                }
                
                # 技術文書のスコアにボーナスを追加（優先順位を高める）
                score_bonus = {
                    '9JIZ7NR5GM': 0.15,  # technical-docs に +0.15 ボーナス
                    'BCI4SYCYPF': 0.08,  # confluence に +0.08 ボーナス
                    'VO92FYFPG6': 0.0   # help page はボーナスなし
                }
                
                # 結果をデータソース別に分類
                results_by_source = {}
                
                for result in response.get('retrievalResults', []):
                    content = result.get('content', {}).get('text', '')
                    location = result.get('location', {})
                    uri = location.get('s3Location', {}).get('uri', '')
                    metadata = result.get('metadata', {})
                    data_source_id = metadata.get('x-amz-bedrock-kb-data-source-id', '')
                    
                    # 記事IDを抽出（URLから）
                    article_id = self._extract_article_id(uri)
                    
                    # コンテンツのハッシュを生成（重複チェック用）
                    content_hash = hash(content[:500])  # 最初の500文字でハッシュ
                    
                    # 重複チェック
                    if content_hash not in seen_content and article_id not in seen_articles:
                        # スコアにボーナスを追加
                        original_score = result.get('score', 0)
                        bonus = score_bonus.get(data_source_id, 0.0)
                        adjusted_score = original_score + bonus
                        
                        result_item = {
                            'content': content,
                            'score': adjusted_score,
                            'original_score': original_score,
                            'location': location,
                            'metadata': metadata,
                            'article_id': article_id,
                            'data_source_id': data_source_id,
                            'priority': data_source_priority.get(data_source_id, 99)
                        }
                        
                        logger.info(f"結果追加: データソース={data_source_id}, 元スコア={original_score:.4f}, 調整後スコア={adjusted_score:.4f}")
                        
                        if data_source_id not in results_by_source:
                            results_by_source[data_source_id] = []
                        results_by_source[data_source_id].append(result_item)
                        
                        seen_content.add(content_hash)
                        seen_articles.add(article_id)
                
                # Technical-docsの結果を上位3位以内に強制表示
                tech_results = results_by_source.get('9JIZ7NR5GM', [])
                non_tech_results = []
                for source_id, source_results in results_by_source.items():
                    if source_id != '9JIZ7NR5GM':
                        non_tech_results.extend(source_results)
                
                # 各グループをスコア順にソート
                tech_results = sorted(tech_results, key=lambda x: x['score'], reverse=True)
                non_tech_results = sorted(non_tech_results, key=lambda x: x['score'], reverse=True)
                
                # 最終結果を組み立て
                final_results = []
                
                # Technical-docsの結果があれば、上位3位以内に必ず含める
                if tech_results:
                    # 最大3つまでのTechnical-docs結果を取得
                    top_tech = tech_results[:min(3, len(tech_results))]
                    final_results.extend(top_tech)
                    logger.info(f"Technical-docs結果を上位に配置: {len(top_tech)}件")
                
                # 残りの枠をnon-tech結果で埋める
                remaining_slots = max_results - len(final_results)
                if remaining_slots > 0:
                    final_results.extend(non_tech_results[:remaining_slots])
                
                # 最終結果
                results = final_results[:max_results]
                
                logger.info(f"データソース別結果数: {[(k, len(v)) for k, v in results_by_source.items()]}")
                logger.info(f"最終結果 (上位{len(results)}件):")
                for i, result in enumerate(results):
                    logger.info(f"  {i+1}. データソース={result['data_source_id']}, 元スコア={result.get('original_score', 0):.4f}, 調整後スコア={result['score']:.4f}")
                
                # 最終的に必要な件数に制限
                results = results[:max_results]
                
                return results
                
            except Exception as e:
                logger.error(f"Knowledge Base検索エラー (試行 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数バックオフ
                else:
                    logger.error("Knowledge Base検索の最大試行回数に達しました")
                    return []
    
    def _extract_article_id(self, uri: str) -> str:
        """URIから記事IDを抽出"""
        import re
        
        # 記事ID（数字）を抽出
        match = re.search(r'_(\d+)[-_]', uri)
        if match:
            return match.group(1)
        
        # 記事IDが見つからない場合はファイル名を使用
        filename = uri.split('/')[-1]
        return filename.split('.')[0]
    
    def format_answer(self, answer: str) -> str:
        """回答を読みやすい形式にフォーマットする"""
        if not answer:
            return answer
            
        logger.info(f"フォーマット開始: {answer[:50]}")
        
        # より精密でバランスの取れた改行処理
        formatted = answer.strip()
        
        # 1. 見出し（## で始まる行）の前後に改行を追加
        formatted = re.sub(r'(?<!\n)(##\s[^\n]+)', r'\n\n\1\n\n', formatted)
        
        # 2. 句点の後に改行を追加（ただし、適切な文脈のみ）
        # 句点の後に日本語文字、*、#、-が続く場合のみ改行を追加
        # 数字やアルファベットの後は改行しない（URLや英数字の途中を避ける）
        formatted = re.sub(r'。\s*(?=[あ-んア-ン一-龯ぁ-ゟ\*\#\-])', '。\n\n', formatted)
        
        # 3. 番号付きリスト項目の処理（より精密に）
        # 番号付きリストの開始の前に改行を追加
        formatted = re.sub(r'(?<!\n)(\d+\.\s)', r'\n\n\1', formatted)
        
        # 4. 箇条書き（- で始まる行）の処理
        # 箇条書きの開始の前に改行を追加
        formatted = re.sub(r'(?<!\n)(- [^\n]+)', r'\n\n\1', formatted)
        
        # 5. **注意**: や **推奨**: の前後に改行を追加
        formatted = re.sub(r'(?<!\n)(\*\*(?:注意|推奨|重要)\*\*:)', r'\n\n\1', formatted)
        
        # 6. コードブロックの前後に改行を追加
        formatted = re.sub(r'(?<!\n)(```)', r'\n\n\1', formatted)
        formatted = re.sub(r'(```)(?!\n)', r'\1\n\n', formatted)
        
        # 7. 長い文章の適度な改行（100文字以上で句点がある場合）
        # 長い段落を適度に分割するが、単語の途中で切らないように注意
        lines = formatted.split('\n')
        processed_lines = []
        for line in lines:
            if len(line) > 100 and '。' in line:
                # 句点の位置で改行を検討
                parts = line.split('。')
                current_part = ''
                for i, part in enumerate(parts):
                    if i < len(parts) - 1:  # 最後の部分以外
                        current_part += part + '。'
                        if len(current_part) > 80:  # 適度な長さになったら改行
                            processed_lines.append(current_part)
                            current_part = ''
                    else:
                        current_part += part
                if current_part:
                    processed_lines.append(current_part)
            else:
                processed_lines.append(line)
        formatted = '\n'.join(processed_lines)
        
        # 8. 連続する3つ以上の改行を2つに制限
        formatted = re.sub(r'\n{3,}', '\n\n', formatted)
        
        # 9. 文頭と文末の不要な改行を除去
        formatted = formatted.strip()
        
        # 10. Markdownの太字をHTMLに変換
        formatted = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', formatted)
        
        # 11. Markdownの見出し（## ）をHTMLに変換
        formatted = re.sub(r'##\s+([^\n]+)', r'<h3>\1</h3>', formatted)
        
        # 12. Web表示用に改行コードをHTMLブレークタグに変換
        formatted = formatted.replace('\n\n', '<br><br>')  # 段落間
        formatted = formatted.replace('\n', '<br>')        # 単一改行
        
        # 13. h3タグの前後の不要な<br>タグを除去
        formatted = re.sub(r'<br><br><h3>', r'<h3>', formatted)  # 見出し前の改行除去
        formatted = re.sub(r'</h3><br><br>', r'</h3>', formatted)  # 見出し後の改行除去
        
        logger.info(f"フォーマット完了: {formatted[:100]}")
        
        return formatted
    
    def generate_answer_with_bedrock(self, query: str, retrieved_context: List[Dict[str, Any]]) -> str:
        """取得したコンテキストを使ってBedrockで回答を生成"""
        import time
        
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                context_text = "\n\n".join([
                    f"関連情報 {i+1}:\n{item['content'][:1000]}..." if len(item['content']) > 1000 else f"関連情報 {i+1}:\n{item['content']}" 
                    for i, item in enumerate(retrieved_context)
                ])
                
                prompt = f"""あなたは多言語化サービスの専門カスタマーサポートAIです。以下の公式ヘルプページ情報を参考にして、ユーザーの質問に正確で詳細な回答を提供してください。

【参考情報】
{context_text}

【質問】
{query}

【回答ガイドライン】
- 必ず日本語で回答する（英語の質問であっても日本語で回答する）
- 多言語化サービスの機能や設定について正確な情報を提供する
- 具体的な手順や設定方法がある場合は、ステップバイステップで説明する
- 技術的な内容も分かりやすく説明する
- 参考情報に基づいて回答し、推測や憶測は避ける
- 日本語で自然で読みやすい文章で回答する

【回答形式】
- 必ず各文章の後に2回改行する（空行を1行入れる）
- 箇条書きの各項目の後も必ず2回改行する
- 番号付きリストの各項目の後も必ず2回改行する
- 見出しは「## 」で始め、見出しの前後に必ず2回改行する
- 重要なポイントは**太字**で強調する
- コードブロックは「```」で囲み、前後に必ず2回改行する
- 注意事項は「**注意**:」で始め、前後に必ず2回改行する
- 結論や推奨事項は「**推奨**:」で始め、前後に必ず2回改行する
- 文章が長い場合は適度に改行して読みやすくする

【回答】"""
                
                # Claudeモデル用のMessages API形式
                if 'anthropic.claude' in self.model_id:
                    body = {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 1000,
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    }
                else:
                    # Titanモデル用のリクエスト形式
                    body = {
                        "inputText": prompt,
                        "textGenerationConfig": {
                            "maxTokenCount": 1000,
                            "temperature": 0.3,
                            "topP": 0.9
                        }
                    }
                
                response = self.bedrock_runtime.invoke_model(
                    body=json.dumps(body),
                    modelId=self.model_id,
                    accept='application/json',
                    contentType='application/json'
                )
                
                response_body = json.loads(response.get('body').read())
                
                # Claudeモデルの場合（Messages API）
                if 'anthropic.claude' in self.model_id:
                    content = response_body.get('content', [])
                    if content and len(content) > 0:
                        return content[0].get('text', '')
                    return ''
                else:
                    # Titanモデルの場合
                    return response_body.get('results', [{}])[0].get('outputText', '')
                
            except Exception as e:
                logger.error(f"回答生成エラー (試行 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数バックオフ
                else:
                    logger.error("回答生成の最大試行回数に達しました")
                    return f"回答の生成中にエラーが発生しました: {str(e)}"
    
    def ask_question(self, query: str) -> Dict[str, Any]:
        """質問応答の実行"""
        logger.info(f"質問を処理中: {query}")
        
        # キャッシュ確認
        query_hash = hash(query.strip().lower())
        if query_hash in self._query_cache:
            logger.info("キャッシュから回答を返します")
            return self._query_cache[query_hash]
        
        # Step 1: Knowledge Baseから関連情報を取得
        retrieved_context = self.retrieve_from_knowledge_base(query)
        
        if not retrieved_context:
            result = {
                'answer': '申し訳ございませんが、関連する情報が見つかりませんでした。',
                'sources': [],
                'confidence': 0
            }
            self._add_to_cache(query_hash, result)
            return result
        
        # Step 2: 取得した情報を使って回答を生成
        raw_answer = self.generate_answer_with_bedrock(query, retrieved_context)
        
        # Step 2.5: 回答をフォーマットして読みやすくする
        answer = self.format_answer(raw_answer)
        logger.info(f"フォーマット前: {repr(raw_answer[:100])}")
        logger.info(f"フォーマット後: {repr(answer[:100])}")
        
        # Step 3: ソース情報を整理
        sources = []
        for item in retrieved_context:
            uri = ''
            if 'location' in item and 's3Location' in item['location']:
                uri = item['location']['s3Location'].get('uri', '')
            elif 'data_source_id' in item:
                # Confluenceなどの外部ソースの場合
                data_source_id = item['data_source_id']
                if data_source_id == 'BCI4SYCYPF':
                    uri = 'Confluence (docs)'
                elif data_source_id == '9JIZ7NR5GM':
                    uri = 'Technical Documentation'
                elif data_source_id == 'VO92FYFPG6':
                    uri = 'Help Page'
                else:
                    uri = f'Data Source: {data_source_id}'
            
            sources.append({
                'uri': uri,
                'score': item['score']
            })
        
        result = {
            'answer': answer,
            'sources': sources,
            'confidence': max([item['score'] for item in retrieved_context]) if retrieved_context else 0,
            'retrieved_context': retrieved_context
        }
        
        # 結果をキャッシュに保存
        self._add_to_cache(query_hash, result)
        
        return result
    
    def _add_to_cache(self, query_hash: int, result: Dict[str, Any]):
        """キャッシュに結果を追加"""
        if len(self._query_cache) >= self._cache_max_size:
            # 最古のエントリを削除
            oldest_key = next(iter(self._query_cache))
            del self._query_cache[oldest_key]
        
        # retrieved_contextを除いてキャッシュに保存（メモリ節約）
        cached_result = {
            'answer': result['answer'],
            'sources': result['sources'],
            'confidence': result['confidence']
        }
        self._query_cache[query_hash] = cached_result

def main():
    # 使用例
    qa_system = BedrockKnowledgeBaseQA()
    
    while True:
        query = input("\n質問を入力してください (終了するには 'quit' と入力): ")
        if query.lower() == 'quit':
            break
        
        if query.strip():
            result = qa_system.ask_question(query)
            print(f"\n回答: {result['answer']}")
            print(f"信頼度: {result['confidence']:.3f}")
            if result['sources']:
                print("参考ソース:")
                for source in result['sources']:
                    print(f"  - {source['uri']} (スコア: {source['score']:.3f})")

if __name__ == "__main__":
    main()