# thoughts-mirror-launcher

ローカルに思考を保存するシンプルなランチャー。  
Drive APIは使わない。Google Driveクライアントに同期を任せる設計。

---

## 何をするか

会話中に「保存して」と言うだけで、思考がローカルのNDJSONファイルに記録される。  
ClaudeがPythonスクリプトを直接実行し、ターミナル操作は不要。

保存先 → `thoughts_mirror/journal_by_day/YYYY/MM/YYYY-MM-DD.ndjson`  
インデックス自動更新 → `thoughts_mirror/indexes/thought_map.json` / `locator.jsonl`

---

## フォルダ構成

```
thoughts_mirror/
  journal_by_day/   ← SSOT（唯一の正）
  indexes/
    thought_map.json
    locator.jsonl
  secrets/
    your-service-account.json   ← 不要（Drive API未使用）
  launcher/
    save_thought.py
```

Google Driveへの同期は、PC上で動いているGoogleドライブクライアントが自動で行う。

---

## 必要なもの

- Python 3.10+
- 外部ライブラリ不要（標準ライブラリのみ）
- Google Driveクライアント（同期したい場合）
- Claude Cowork（または任意のAIエージェント実行環境）

---

## セットアップ

1. `thoughts_mirror/` フォルダを任意の場所に作成
2. `journal_by_day/` と `indexes/` サブフォルダを作成
3. `save_thought.py` を `thoughts_mirror/launcher/` に配置
4. `thoughts_mirror/` をClaudeのコンテキストフォルダとして追加

---

## 使い方

### CLIから直接実行

```bash
echo '{"author":"yourname","record":{"type":"thought","text":"保存したい内容","tags":["tag1","tag2"]}}' \
  | python save_thought.py --mirror /path/to/thoughts_mirror/
```

### Claude（Cowork）から実行

会話中に「このアイデアを保存して」と言うだけ。  
ClaudeがJSONを組み立て、スクリプトを実行する。

---

## レコード形式

```json
{
  "id": "abc123def456",
  "t_utc": "2026-06-22T00:09:16.515454Z",
  "author": "yourname",
  "prev_hash": "前レコードのhash（ハッシュ連鎖）",
  "hash": "sha256ハッシュ（64文字）",
  "algo": "sha256({t_utc,prev_hash,record})",
  "v": 1,
  "record": {
    "type": "thought",
    "text": "保存したい内容",
    "tags": ["tag1", "tag2"]
  }
}
```

ハッシュ連鎖により、レコードの改ざん検知が可能。

---

## 以前のバージョン（Drive API版）

Google DriveにAPIで直接書き込みたい場合、または  
GeminiやChatGPTなど他のAIと組み合わせたい場合は旧バージョンを使用してください。

→ [thoughts_store_backend](https://github.com/Ryosuke-Tanabe/thoughts_store_backend)（Drive API対応、Bridge方式）

---

## 設計思想

- **SSOT**（Single Source of Truth）：`journal_by_day/` のNDJSONイベント列が唯一の正
- **ローカルファースト**：Drive APIに依存しない。同期はOSに任せる
- **Full Rebuild**：インデックスは差分更新せず、常に全量再生成可能
- **append-only**：既存レコードは修正・削除しない

詳細仕様 → `SkillDays_job_launcher_v1_5_0.md`
