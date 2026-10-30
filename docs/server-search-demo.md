# AlopexDB GraphRAGサーバー検索デモ（2026-10-30）

## 目的と範囲

少量の文書をHTTPで登録し、AlopexDBへのSQL・ベクトル保存、エンティティ抽出、
Leidenコミュニティ検出、local/global検索までの接続を確認するための実演です。
実際の `POST /v1/documents` と `POST /v1/search` を利用します。
LLMと埋め込みだけを決定的なローカル実装に置き換えます。
意味検索の精度、自然言語からの抽出能力、回答品質、速度のベンチマークには使用しません。

照合元はmainの `d42c2fa7404491584c9072258d7c621cf322575b`（PR #3）。
既存の `make server-test` はヘルスチェックと2ベクトルのHNSW検索だけです。
既存APIテストはサービス呼び出しをmockに置換しており、実DBへの登録確認とは区別します。

## 実行

Docker Engine、Docker Compose v2（`up --wait` 対応）、Python 3、makeを用意します。
初回のイメージ・Python依存・AlopexDB 0.8.16バイナリ取得にはネットワークが必要です。
Python依存は既存のDockerfileと `pdm.lock` を使います。APIキー・モデルダウンロードは不要です。

```bash
make demo-unit-test
make server-demo
make server-demo-verify
make server-demo-restart
make server-demo-down
```

`server-demo` はビルド・起動・ヘルス待機・2文書登録・local/global/auto検索を順に実行し、
HTTP応答をJSONで標準出力に表示します。起動待機は180秒、各HTTP要求は60秒で打ち切ります。
`server-demo-verify` は登録を行わず、保存済みデータを検索します。
`server-demo-restart` はDB/API両方を再起動してから同じ検索を検証します。
失敗時は終了コードが非ゼロになり、コンテナを残すので以下で調査できます。

```bash
bash scripts/server_demo.sh logs
PYTHONPATH=src python3 -m graphrag_anthropic_llamaindex.server_demo --verify-only > demo-results.json
```

ホスト公開先は `127.0.0.1:18000`。通常サーバーの8000番とは別です。
Composeプロジェクト名は `graphrag-search-demo` に固定し、専用ボリュームを使用します。
実行時ネットワークはinternalで、外部LLMへの接続と通常環境の資格情報マウントを含みません。
終了操作はデータを保持します。最初からやり直す場合のみ、次のコマンドでデモ専用データを削除します。

```bash
docker compose -p graphrag-search-demo -f docker/docker-compose.demo.yml down --volumes
make server-demo
```

## サンプルと合格条件

文書は `demo_fixture.py` の `DOCUMENTS` にあります。
`demo-storage.txt` はAlopexDB/LlamaIndex/GraphRAGの三角形、
`demo-service.txt` はGraphRAG/SearchDemo/AlopexDBの三角形を表す架空の説明文です。
`Source connects Target.` を解析する固定ルールでエンティティと関係を抽出します。
要約と検索出力には `[DEMO FIXTURE]` を付け、取得したコンテキストをそのまま示します。
埋め込みはSHA-256による64次元の単語ハッシュで、意味表現ではありません。

| 検証 | 合格条件 |
|---|---|
| 接続 | healthがAlopexDB正常、かつ `runtime: demo-fixture-v1`。通常サーバーへの誤登録は実行前に拒否 |
| 登録 | 2文書それぞれが `status: indexed` と送信したfilenameを返す |
| local | 結果あり、正の有限score、エラーなし、fixtureとAlopexDBを含むtext、2件以上のentities |
| global | 上記の結果検証に加え、`search_type: global` と空でないコミュニティ `report_ids` |
| auto | overviewクエリがglobalへ選択され、同じ検証に成功 |
| 再起動後 | 新規登録せずlocal/global/autoの検証に成功 |

同じ文書を再送すると既存の文書ハッシュによるスキップ経路を使います。
登録APIの `indexed` は新規処理件数を返さないため、この表示だけでは重複件数ゼロを証明しません。
UUID・処理時間・内部順序は固定していません。JSONの完全一致ではなく上記の意味的条件を検証します。

## 検索と回答生成の境界

APIは `results: [{score, text, metadata}]` を返します。専用の回答APIはありません。
ただしlocal retrieverはLLMで応答を作り、global retrieverはMap/Reduceで最終応答を作ります。
`_retrieve` という名前だけでは外部LLM呼び出しの有無を判断できません。
今回、globalのコミュニティ候補取得を `as_query_engine().query()` から
`as_retriever().retrieve()` に変更し、候補取得段階の不要な回答生成を除いています。
通常プロバイダでの登録・Map/Reduce・local応答生成は引き続きLLMを使用します。

localの `relationships` は現状空の初期値で、text unitsも空リストを渡しています。
そのため本実演を「関係を辿った根拠付き回答が完成している」と紹介するのは避け、
「文書登録、AlopexDB保存、エンティティ・コミュニティ検索の接続確認」と説明してください。
globalのreport IDはコミュニティノード由来で、元文書の完全な引用・追跡保証とは区別します。
DRIFTは本デモの合格条件に含めていません。

## この変更で確認できた結果

2026-10-30の作業環境で `make demo-unit-test` の7件が成功しました。
固定ルール、埋め込み、課金プロバイダへの誤接続防止、HTTP要求形式、登録失敗、
空結果・エラーノード・根拠不足の検出を検証しています。
HTTPテストの相手は標準ライブラリで作った偽サーバーです。
実際のFastAPI、AlopexDB、LlamaIndexを動作確認した結果ではありません。
Python構文コンパイル、bash構文、差分の空白チェックも成功しました。

この環境にはDocker/PDM/pytest/LlamaIndex/Alopexの実行依存がないため、
Composeビルド、実サーバーE2E、再起動後の永続化、既存pytest一式と
`test_demo_models.py` のアダプタ検証は未実行です。
依存導入後は `pdm run pytest -q`、Docker環境では上記3つのデモ検証を実行してください。
実LLM・実埋め込みの品質評価と課金検証は今回の対象外です。
