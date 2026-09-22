"""
模組 G：AI Orchestration Agent
❼_ AI招募助手.py — Streamlit Chat UI

功能：
  - 提供對話介面，HR 輸入需求後由 Agent 自動執行對應模組
  - 支援兩種使用情境：
      1. 有 JD：執行 A→B→D，依需求選擇性加跑 C / E，產出整合報告
      2. 無 JD：執行 Module F（HR 知識問答）
  - 側邊欄提供公司設定檔與 JD 輸入區
  - 對話區顯示執行路徑（steps_taken）與錯誤訊息（若有）
"""

import requests
import streamlit as st

API_URL = "http://localhost:8000/api/v1/run-agent"

# ── 頁面設定 ─────────────────────────────────────────────────

st.set_page_config(page_title="AI 招募助手", page_icon="🤖")
st.title("🤖 AI 招募助手")
st.caption("輸入您的招募需求，AI 將自動分析並產出整合報告")

# ── 側邊欄：JD 與公司資料輸入 ────────────────────────────────

with st.sidebar:
    st.header("📋 招募資料設定")
    st.caption("填寫後送出問題，Agent 將自動判斷執行哪些模組")

    job_title = st.text_input("職稱", placeholder="例：資深後端工程師")

    jd_text = st.text_area(
        "JD 文字（選填）",
        placeholder="貼上完整職缺描述...",
        height=200,
    )

    st.markdown("---")
    st.subheader("🏢 公司設定檔")
    st.caption("提供 JD 時必填，供 Module B 改寫使用")

    company_name = st.text_input("公司名稱", placeholder="例：台灣新創股份有限公司")
    vision = st.text_input("公司願景", placeholder="例：打造亞洲最具影響力的 HR SaaS 平台")
    culture_keywords_input = st.text_input(
        "文化關鍵字（逗號分隔）",
        placeholder="例：自驅、透明、快速迭代",
    )
    industry_context = st.text_input("產業背景", placeholder="例：HR SaaS、B2B 軟體")
    company_type = st.selectbox(
        "公司類型（選填）",
        options=["", "新創", "中小企業", "大型企業", "外商"],
    )
    seniority_level = st.selectbox(
        "職級（選填）",
        options=["", "Junior", "Mid", "Senior", "Lead", "Manager"],
    )

# ── 對話紀錄初始化 ────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

# 顯示歷史對話
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── 使用者輸入 ────────────────────────────────────────────────

user_input = st.chat_input("請輸入您的招募需求或 HR 問題...")

if user_input:
    # 顯示使用者訊息
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 組裝 company_profile（有 JD 時才傳）
    company_profile = None
    if jd_text and company_name:
        culture_keywords = [k.strip() for k in culture_keywords_input.split("，") if k.strip()]
        # 中文逗號分隔，同時支援英文逗號
        if not culture_keywords:
            culture_keywords = [k.strip() for k in culture_keywords_input.split(",") if k.strip()]

        company_profile = {
            "company_name": company_name,
            "vision": vision,
            "culture_keywords": culture_keywords,
            "industry_context": industry_context or None,
            "company_type": company_type or None,
            "seniority_level": seniority_level or None,
        }

    # 組裝 request payload
    payload = {
        "user_input": user_input,
        "job_title": job_title or None,
        "jd_text": jd_text or None,
        "company_profile": company_profile,
    }

    # 呼叫 API
    with st.chat_message("assistant"):
        with st.spinner("Agent 執行中，請稍候..."):
            try:
                response = requests.post(API_URL, json=payload, timeout=120)
                response.raise_for_status()
                data = response.json()

                final_report = data.get("final_report", "")
                steps_taken = data.get("steps_taken", [])
                error_messages = data.get("error_messages", [])

                # 顯示執行路徑
                if steps_taken:
                    steps_display = " → ".join(steps_taken)
                    st.caption(f"✅ 執行模組：{steps_display}")

                # 顯示錯誤訊息（若有）
                if error_messages:
                    with st.expander("⚠️ 執行過程中的警告訊息", expanded=False):
                        for err in error_messages:
                            st.warning(err)

                # 顯示最終報告
                st.markdown(final_report)

                # 儲存 assistant 訊息
                assistant_content = f"✅ 執行模組：{steps_display}\n\n{final_report}" if steps_taken else final_report
                st.session_state.messages.append({"role": "assistant", "content": assistant_content})

            except requests.exceptions.Timeout:
                err_msg = "⏱️ Agent 執行逾時（超過 120 秒），請稍後再試。"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})

            except requests.exceptions.HTTPError as e:
                detail = ""
                try:
                    detail = e.response.json().get("detail", "")
                except Exception:
                    pass
                err_msg = f"❌ 請求錯誤：{detail or str(e)}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})

            except Exception as e:
                err_msg = f"❌ 發生未預期錯誤：{e}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})