下記の GitHub イベントについて、sunwood-community skillを使って解説投稿を作成してください。

対象イベント:
- 種別: {{event_type}}
- 対象: {{event_target}}
- URL: {{event_url}}
- 公開日時: {{published_at}}

解説作成の手順:
1. まず、調査レポート Markdown を作成してください。
2. イベント内容を分析してください。キーワード、トピック、技術用語を抽出してください。
3. Web検索で関連する公式情報、技術文書、論文を収集してください。
4. 調査レポートに、要約、技術要点、関連情報、時系列の見解を整理してください。
5. 文脈を理解した充実した解説を作成してください。
6. 投稿直前に、`skills/sunwood-community/scripts/post_thread.py` 用の payload JSON を作成してください。
7. 本体投稿、画像添付、複数リプライは、その payload を使って `post_thread.py --payload-file ...` を1回だけ実行して投稿してください。

共通投稿ルール:
`prompts/shared_posting_rules.md` を適用してください。

GitHub event 固有ルール:
- 参照URLとして使うのは X のポストURLではなく、GitHub の release / repository URL です。
- GitHub event のリプライには、その URL を読むと何が確認できるのかを短く添えてください。
- 図解画像を作る場合は、調査レポート Markdown を元に日本語で図解してください。

解説の要件:
- `prompts/shared_explainer_requirements.md` を適用してください。
- 時系列の流れや背景があれば短く触れる

結果には必ず以下を含めてください:
- `prompts/shared_result_requirements.md` を適用してください。
