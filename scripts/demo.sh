#!/bin/bash

set -euo pipefail
cd "$(dirname "$0")/.."
CONFIG="${1:-config/config.yaml}"
if [[ ! -f "$CONFIG" ]]; then
    echo "設定ファイルがありません: $CONFIG (config/config.example.yaml をコピーしてください)" >&2
    exit 1
fi
echo "組み込み構成のデモです。設定したLLMの利用料金が発生する場合があります。"

# デモスクリプト：GraphRAG with LlamaIndex and Anthropic の機能紹介

echo "==================================================="
echo "GraphRAG with LlamaIndex and Anthropic デモスクリプト"
echo "==================================================="

# 1. 環境のセットアップ
echo "1. 依存関係のインストール (pdm install)..."
pdm install
if [ $? -ne 0 ]; then
    echo "エラー: pdm install に失敗しました。環境を確認してください。"
    exit 1
fi
echo "インストール完了。"

# 2. データの追加と処理
echo -e "\n2. ドキュメントの追加と処理 (エンティティ/リレーションシップ抽出、コミュニティ検出/要約)..."
echo "   (初回実行時はLLM呼び出しとモデルダウンロードに時間がかかります)"
pdm run python -m graphrag_anthropic_llamaindex.main --config "$CONFIG" add
if [ $? -ne 0 ]; then
    echo "エラー: ドキュメントの追加処理に失敗しました。"
    exit 1
fi
echo "ドキュメント処理完了。"

# 3. 検索機能のデモンストレーション

echo -e "\n3. 検索機能のデモンストレーション:"

# 3.1. エンティティ中心のlocal検索
echo -e "\n--- 3.1. エンティティ中心のlocal検索 ---"
echo "クエリ: \"AIの最新動向について教えてください\""
pdm run python -m graphrag_anthropic_llamaindex.main --config "$CONFIG" search "AIの最新動向について教えてください" --mode local

# 3.2. エンティティインデックスの検索
echo -e "\n--- 3.2. エンティティインデックスの検索 ---"
echo "クエリ: \"Acme CorpのCEOは誰ですか？\""
pdm run python -m graphrag_anthropic_llamaindex.main --config "$CONFIG" search "Acme CorpのCEOは誰ですか？" --mode local

# 3.3. コミュニティ要約インデックスの検索
echo -e "\n--- 3.3. コミュニティ要約インデックスの検索 ---"
echo "クエリ: \"サステナブルテクノロジーに関するコミュニティはありますか？\""
pdm run python -m graphrag_anthropic_llamaindex.main --config "$CONFIG" search "サステナブルテクノロジーに関するコミュニティはありますか？" --mode global

# 3.4. クエリに応じたモード自動選択
echo -e "\n--- 3.4. クエリに応じたモード自動選択 ---"
echo "クエリ: \"気候変動に関する主要な研究機関は？\""
pdm run python -m graphrag_anthropic_llamaindex.main --config "$CONFIG" search "気候変動に関する主要な研究機関は？" --mode auto

echo -e "\n==================================================="
echo "デモスクリプト完了。"
echo "==================================================="
