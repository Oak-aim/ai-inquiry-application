from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import google.generativeai as genai
import json
import os

app = FastAPI()

# Gemini API Key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-1.5-flash")

DATA_FILE = "data/inquiries.json"


# --------------------------------------------------
# Pydantic Models
# --------------------------------------------------

class InquiryRequest(BaseModel):
    question: str


class InquiryRecord(BaseModel):
    id: int
    created_at: str
    question: str
    category: str
    urgency: str
    answer: str


# --------------------------------------------------
# JSON Functions
# --------------------------------------------------

def load_inquiries():

    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_inquiry(record):

    inquiries = load_inquiries()

    inquiries.append(record)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            inquiries,
            f,
            ensure_ascii=False,
            indent=2
        )


def find_by_id(inquiry_id):

    inquiries = load_inquiries()

    for inquiry in inquiries:
        if inquiry["id"] == inquiry_id:
            return inquiry

    return None


# --------------------------------------------------
# POST /inquiries
# --------------------------------------------------

@app.post("/inquiries", status_code=201)
def create_inquiry(request: InquiryRequest):

    if request.question.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="question is required"
        )

    prompt = f"""
あなたは社内問い合わせ対応AIです。

以下の問い合わせ内容を分析し、
カテゴリー・緊急度・回答案を生成してください。

【カテゴリー】
- 勤怠
- 休暇
- 給与
- 経費精算
- 社員情報変更
- その他

【緊急度】
- 高
- 中
- 低

以下のJSON形式のみで返してください。

{{
  "category": "...",
  "urgency": "...",
  "answer": "..."
}}

問い合わせ内容：
{request.question}
"""

    try:

        response = model.generate_content(prompt)

        text = response.text.strip()

        # ```json 제거w
        text = text.replace("```json", "")
        text = text.replace("```", "")

        result = json.loads(text)

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Gemini API connection failed"
        )

    inquiries = load_inquiries()

    new_record = {
        "id": len(inquiries) + 1,
        "created_at": datetime.now().isoformat(),
        "question": request.question,
        "category": result["category"],
        "urgency": result["urgency"],
        "answer": result["answer"]
    }

    save_inquiry(new_record)

    return new_record


# --------------------------------------------------
# GET /inquiries
# --------------------------------------------------

@app.get("/inquiries")
def get_inquiries():

    inquiries = load_inquiries()

    inquiries.sort(
        key=lambda x: x["created_at"],
        reverse=True
    )

    return inquiries


# --------------------------------------------------
# GET /inquiries/{id}
# --------------------------------------------------

@app.get("/inquiries/{inquiry_id}")
def get_inquiry(inquiry_id: int):

    inquiry = find_by_id(inquiry_id)

    if inquiry is None:
        raise HTTPException(
            status_code=404,
            detail="Inquiry not found"
        )

    return inquiry