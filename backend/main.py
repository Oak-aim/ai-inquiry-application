import os
import json
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
from backend.storage import save_inquiry, get_all_inquiries, get_inquiry_by_id

# .env読み込み
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY が設定されていません。")

# Gemini 設定
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash-lite")

app = FastAPI(title="AI Inquiry API", version="1.0.0")

# VALID_CATEGORIES = ["勤怠", "休暇", "給与", "経費精算", "社員情報変更", "その他"]
# VALID_URGENCIES = ["高", "中", "低"]


class InquiryRequest(BaseModel):
    question: str

# ルート確認
@app.get("/")
def root():
    return {"message": "AI Inquiry API is running"}

# POST /inquiries  問い合わせ登録・AI処理・保存
@app.post("/inquiries", status_code=201)
def create_inquiry(request: InquiryRequest):
    if request.question.strip() == "":
        raise HTTPException(
            status_code=400, 
            detail="問い合わせ内容を入力してください。")

    prompt = f"""
あなたは社内総務の問い合わせ対応AIです。
以下の問い合わせ内容を分析し、必ず下記のJSON形式のみで返してください。
前置きや説明文、マークダウン記法（```json など）は一切不要です。

以下のJSON形式のみで返してください。

{{
  "category": "勤怠 または 休暇 または 給与 または 経費精算 または 社員情報変更 または その他 のいずれか1つ",
  "urgency": "高 または 中 または 低 のいずれか1つ",
  "answer": "問い合わせへの丁寧な回答文（150文字以上）"
}}

問い合わせ内容：
{request.question}
"""

    try:
        response = model.generate_content(prompt)

        raw = response.text.strip()

        # マークダウンコードブロックの除去
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        ai_result = json.loads(raw)

    except json.JSONDecodeError:  # AIの応答がJSONとして解析できない場合
        raise HTTPException(status_code=500, 
                            detail="AI の応答を JSON として解析できませんでした。再度お試しください。"
                            )
    except Exception as e:        # その他のエラー（APIエラーなど）
        raise HTTPException(status_code=500, 
                            detail=f"AI 処理中にエラーが発生しました: {str(e)}"
                            )

    # バリデーション
    category = ai_result.get("category", "その他")
    urgency = ai_result.get("urgency", "中")
    answer = ai_result.get("answer", "")

    # if category not in VALID_CATEGORIES:
    #     category = "その他"
    # if urgency not in VALID_URGENCIES:
    #     urgency = "中"

    record = save_inquiry(
        question=request.question,
        category=category,
        urgency=urgency,
        answer=answer,
    )
    return record

# GET /inquiries  問い合わせ一覧取得
@app.get("/inquiries")
def list_inquiries():
    return get_all_inquiries()

# GET /inquiries/{id}  問い合わせ詳細取得
@app.get("/inquiries/{inquiry_id}")
def get_inquiry(inquiry_id: int):
    record = get_inquiry_by_id(inquiry_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"ID {inquiry_id} の問い合わせが見つかりません。")
    return record

