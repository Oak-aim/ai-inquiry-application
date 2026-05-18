import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "inquiries.json")
JST = timezone(timedelta(hours=9))


def _load() -> list[dict]:
    """JSONファイルからデータを読み込む"""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save(data: list[dict]) -> None:
    """JSONファイルへデータを書き込む"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_inquiry(question: str, category: str, urgency: str, answer: str) -> dict:
    """問い合わせを保存し、保存したデータを返す"""
    data = _load()

    new_id = max((item["id"] for item in data), default=0) + 1
    now = datetime.now(JST).isoformat()

    record = {
        "id": new_id,
        "created_at": now,
        "question": question,
        "category": category,
        "urgency": urgency,
        "answer": answer,
    }

    data.append(record)
    _save(data)
    return record


def get_all_inquiries() -> list[dict]:
    """全問い合わせを新しい順で返す"""
    data = _load()
    return sorted(data, key=lambda x: x["id"], reverse=True)


def get_inquiry_by_id(inquiry_id: int) -> Optional[dict]:
    """IDで問い合わせを取得する"""
    data = _load()
    for item in data:
        if item["id"] == inquiry_id:
            return item
    return None