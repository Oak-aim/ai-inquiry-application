import streamlit as st
import requests
from datetime import datetime

API_BASE = "http://localhost:8000"

# ページ設定
# st.set_page_config(
#     page_title="AI 問い合わせアプリ",
#     page_icon="💬",
#     layout="wide",
# )

# カスタム CSS
# st.markdown(
#     """
#     <style>
#     .urgency-high   { color: #d32f2f; font-weight: bold; }
#     .urgency-medium { color: #f57c00; font-weight: bold; }
#     .urgency-low    { color: #388e3c; font-weight: bold; }
#     .responseult-box {
#         background: #f5f5f5;
#         border-left: 4px solid #1976d2;
#         padding: 1rem 1.2rem;
#         border-radius: 4px;
#         margin-top: 0.5rem;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True,
# )

# ヘルパー関数
def urgency_html(urgency: str) -> str:
    cls = {"高": "urgency-high", "中": "urgency-medium", "低": "urgency-low"}.get(urgency, "")
    return f'<span class="{cls}">{urgency}</span>'


def fetch_inquiries() -> list[dict]:
    try:
        response = requests.get(f"{API_BASE}/inquiries", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("バックエンド API に接続できません。`uvicorn backend.main:app` が起動しているか確認してください。")
        return []
    except Exception as e:
        st.error(f"一覧の取得に失敗しました: {e}")
        return []


def fetch_inquiry(inquiry_id: int) -> dict | None:
    try:
        response = requests.get(f"{API_BASE}/inquiries/{inquiry_id}", timeout=10)
        if response.status_code == 404:
            st.error("該当する問い合わせが見つかりませんでした。")
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("バックエンド API に接続できません。")
        return None
    except Exception as e:
        st.error(f"詳細の取得に失敗しました: {e}")
        return None

# セッション初期化
if "page" not in st.session_state:
    st.session_state.page = "問い合わせ入力"
if "detail_id" not in st.session_state:
    st.session_state.detail_id = None

# サイドバー（ボタン方式でセッションと競合しない）
st.sidebar.title("AI 問い合わせアプリ")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "メニュー",
    ["問い合わせ入力", "一覧表示"]
)

st.session_state.page = page

st.sidebar.markdown("---")
st.sidebar.caption(f"現在: {st.session_state.page}")

# 問い合わせ入力画面
if st.session_state.page == "問い合わせ入力":
    st.title("問い合わせ入力")
    st.write("総務への問い合わせ内容を入力してください。AI が自動でカテゴリー・緊急度を判定し、回答案を生成します。")

    with st.form("inquiry_form"):
        question = st.text_area(
            "問い合わせ内容",
            height=150,
        )
        submitted = st.form_submit_button("送信", type="primary")

    if submitted:
        if not question.strip():
            st.error("問い合わせ内容を入力してください。")
        else:
            with st.spinner("AI 回答生成中..."):
                try:
                    response = requests.post(
                        f"{API_BASE}/inquiries",
                        json={
                            "question": question
                        },
                        timeout=60,
                    )

                    if response.status_code == 201:
                        data = response.json()
                        # st.success("問い合わせを登録しました。")

                        st.write(f"**カテゴリー：** {data['category']}")
                        st.write(f"**緊急度：** {data['urgency']}")
                        st.write(f"**回答案：** {data['answer']}")

                        # st.caption(f"登録ID: {data['id']} ／ 登録時刻: {data['created_at']}")

                    # elif response.status_code == 422:
                    #     detail = response.json().get("detail", "入力内容を確認してください。")
                    #     st.error(f"{detail}")
                    else:
                        detail = response.json().get("detail", "不明なエラーが発生しました。")
                        st.error(f"サーバーエラー: {detail}")

                except requests.exceptions.ConnectionError:
                    st.error("バックエンド API に接続できません。FastAPI が起動しているか確認してください。")
                except requests.exceptions.Timeout:
                    st.error("AI の処理がタイムアウトしました。再度お試しください。")
                except Exception as e:
                    st.error(f"予期しないエラーが発生しました: {e}")

# 一覧表示画面
elif st.session_state.page == "一覧表示":
    st.title("問い合わせ一覧")

    inquiries = fetch_inquiries()

    if not inquiries:
        st.info("登録された問い合わせはありません。")
    else:
        # st.write(f"全 **{len(inquiries)}** 件")

        # ヘッダー行
        header = st.columns([1, 2.5, 4, 2, 1.5]) # 列幅の比率を指定
        header[0].markdown("**ID**")
        header[1].markdown("**登録時刻**")
        header[2].markdown("**問い合わせ内容**")
        header[3].markdown("**カテゴリー**")
        header[4].markdown("**詳細**")

        st.divider() # 区切り線

        for item in inquiries:
            col_id, col_time, col_q, col_cat, col_btn = st.columns([1, 2.5, 4, 2, 1.5])
            col_id.write(item["id"])
            # ISO 8601 を見やすく整形
            created = datetime.fromisoformat(item["created_at"]).strftime("%Y-%m-%d %H:%M")
            col_time.write(created)
            # 長い問い合わせは省略表示
            q_short = item["question"][:20] + "…" if len(item["question"]) > 20 else item["question"]
            col_q.write(q_short)
            col_cat.write(item["category"])
            if col_btn.button("詳細", key=f"detail_{item['id']}", type="primary"):
                st.session_state.page = "詳細表示"
                st.session_state.detail_id = item["id"]
                st.rerun()

# 詳細表示画面
elif st.session_state.page == "詳細表示":
    if st.button("一覧に戻る"):
        st.session_state.page = "一覧表示"
        st.session_state.detail_id = None
        st.rerun()

    inquiry_id = st.session_state.detail_id
    if inquiry_id is None:
        st.warning("詳細を表示する問い合わせが選択されていません。")
    else:
        data = fetch_inquiry(inquiry_id)
        if data:
            st.title(f"問い合わせ詳細（ID: {data['id']}）")
            st.divider()

            created = datetime.fromisoformat(data["created_at"]).strftime("%Y-%m-%d %H:%M")

            # col1, col2, col3 = st.columns(3)
            st.write("**登録時刻**：", created)
            st.write("**カテゴリー**：", data["category"])
            st.markdown(
                f"**緊急度**：{urgency_html(data['urgency'])}",
                unsafe_allow_html=True, #急度の色分け、HTMLは無効化されるので、そのまま文字として表示される
            )

            st.subheader("問い合わせ内容")
            st.write(data["question"])

            st.subheader("AI 回答案")
            st.markdown(
                f'<div class="responseult-box">{data["answer"]}</div>',
                unsafe_allow_html=True,
            )