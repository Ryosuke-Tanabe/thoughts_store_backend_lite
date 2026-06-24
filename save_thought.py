# -*- coding: utf-8 -*-
"""
save_thought.py — Claudeがローカルに直接thoughtを保存するスクリプト

Usage:
    echo '<JSON>' | python save_thought.py --mirror /path/to/thoughts_mirror/

Arguments:
    --mirror    thoughts_mirrorのベースパス（journal_by_day/, indexes/ を含む親フォルダ）
    stdin       保存するthoughtのJSON（1行）

Drive同期はBridgeに任せる。このスクリプトはローカルのみ。
date_local はJST（UTC+9）で決定する。
"""

import json, hashlib, datetime as dt, os, sys, argparse
from typing import Optional, Dict

UTC = dt.timezone.utc
JST = dt.timezone(dt.timedelta(hours=9))


def utc_now_iso() -> str:
    return dt.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def to_jst(t_utc_str: str) -> dt.datetime:
    """UTC ISO文字列をJSTのdatetimeに変換する"""
    return dt.datetime.fromisoformat(t_utc_str.replace("Z", "+00:00")).astimezone(JST)


def parse_last(ndjson: str) -> Optional[Dict]:
    if not ndjson.strip():
        return None
    try:
        return json.loads(ndjson.strip().splitlines()[-1])
    except Exception:
        return None


def build_record(author: str, prev_hash: Optional[str], record: Dict) -> Dict:
    t_utc = utc_now_iso()
    payload = json.dumps(
        {"t_utc": t_utc, "prev_hash": prev_hash, "record": record},
        ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    h = sha256_hex(payload)
    return {
        "id": h[:12], "t_utc": t_utc, "author": author,
        "prev_hash": prev_hash, "hash": h,
        "algo": "sha256({t_utc,prev_hash,record})", "v": 1, "record": record,
    }


def jst_date_parts(t_utc_str: str) -> tuple[str, str, str]:
    """t_utc文字列からJSTのyyyy, mm, ymdを返す"""
    jst = to_jst(t_utc_str)
    yyyy = f"{jst.year:04d}"
    mm = f"{jst.month:02d}"
    ymd = f"{jst.year:04d}-{jst.month:02d}-{jst.day:02d}"
    return yyyy, mm, ymd


def write_journal(mirror_base: str, record_obj: Dict) -> tuple[str, int]:
    """journal_by_day に追記し (filename, line_num) を返す"""
    yyyy, mm, ymd = jst_date_parts(record_obj["t_utc"])
    filename = f"{ymd}.ndjson"

    local_dir = os.path.join(mirror_base, "journal_by_day", yyyy, mm)
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, filename)

    existing = ""
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            existing = f.read()

    line_num = len([l for l in existing.splitlines() if l.strip()]) + 1

    with open(local_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record_obj, ensure_ascii=False) + "\n")

    return filename, line_num


def get_prev_hash(mirror_base: str) -> Optional[str]:
    """今日（JST）のファイルの最終ハッシュを返す"""
    now_jst = dt.datetime.now(JST)
    yyyy = f"{now_jst.year:04d}"
    mm = f"{now_jst.month:02d}"
    ymd = f"{now_jst.year:04d}-{now_jst.month:02d}-{now_jst.day:02d}"
    path = os.path.join(mirror_base, "journal_by_day", yyyy, mm, f"{ymd}.ndjson")

    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    last = parse_last(content)
    return last.get("hash") if last else None


def update_indexes(mirror_base: str, record_obj: Dict, filename: str, line_num: int) -> None:
    """thought_map.json と locator.jsonl をローカルで更新する"""
    indexes_dir = os.path.join(mirror_base, "indexes")
    os.makedirs(indexes_dir, exist_ok=True)

    inner = record_obj.get("record", {})
    tags = inner.get("tags", [])
    title = inner.get("title", "")
    text = inner.get("text", "")
    text_head = (title or text)[:80]
    # date_local もJSTで決定
    _, _, date_local = jst_date_parts(record_obj["t_utc"])
    full_hash = record_obj["hash"]

    # --- thought_map.json ---
    thought_map_path = os.path.join(indexes_dir, "thought_map.json")
    try:
        if os.path.exists(thought_map_path):
            with open(thought_map_path, "r", encoding="utf-8") as f:
                tm = json.load(f)
        else:
            tm = {"meta": {"version": "local", "build_utc": record_obj["t_utc"],
                           "record_count": 0, "input_files": []}, "thoughts": []}

        tm["thoughts"].append({
            "id": full_hash,
            "type": "thought",
            "t_utc": record_obj["t_utc"],
            "date_local": date_local,
            "tags": tags,
            "text_head": text_head,
            "source": {"file": filename, "line": line_num},
            "source_is_build_time": False,
            "inferred_context_thread": None,
            "inferred_context_event_id": None,
            "inference_rule": None,
        })
        tm["meta"]["record_count"] = len(tm["thoughts"])
        if filename not in tm["meta"].get("input_files", []):
            tm["meta"].setdefault("input_files", []).append(filename)

        with open(thought_map_path, "w", encoding="utf-8") as f:
            json.dump(tm, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ thought_map.json 更新失敗: {e}", file=sys.stderr)

    # --- locator.jsonl ---
    locator_path = os.path.join(indexes_dir, "locator.jsonl")
    try:
        with open(locator_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "id": full_hash,
                "type": "thought",
                "t_utc": record_obj["t_utc"],
                "date_local": date_local,
                "tags": tags,
                "text_head": text_head,
                "source": {"file": filename, "line": line_num},
                "source_is_build_time": False,
            }, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"⚠️ locator.jsonl 更新失敗: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mirror", required=True, help="thoughts_mirror フォルダパス")
    args = parser.parse_args()

    raw = sys.stdin.read().strip()
    if not raw:
        print("❌ stdin が空です", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(raw)
    author = payload.get("author", "unknown")
    record = payload.get("record", {})
    if not record:
        print("❌ record が空です", file=sys.stderr)
        sys.exit(1)

    prev_hash = get_prev_hash(args.mirror)
    record_obj = build_record(author, prev_hash, record)

    filename, line_num = write_journal(args.mirror, record_obj)
    update_indexes(args.mirror, record_obj, filename, line_num)

    print(json.dumps({
        "status": "ok",
        "file": filename,
        "line": line_num,
        "hash": record_obj["hash"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
