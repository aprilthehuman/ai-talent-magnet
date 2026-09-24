"""
模組 G：AI Orchestration Agent
❼_ AI招募助手.py — Streamlit Chat UI

v1.7 UI 改版：
  - 側邊欄大幅簡化：只保留職稱與 JD 文字框
    （公司資料、薪資等改由 parse_input_node 從 Prompt 自動抽取）
  - 主畫面右側加入提示說明，引導使用者如何撰寫 Prompt
  - 若 Agent 回傳 clarification_needed，前端顯示提問而非空白回應
  - 向下相容：前端若仍傳入結構化欄位，parse_input_node 會優先使用

功能：
  - 提供對話介面，HR 輸入需求後由 Agent 自動執行對應模組
  - 支援兩種使用情境：
      1. 有 JD：執行 A→B→D，依需求選擇性加跑 C / E，產出整合報告
      2. 無 JD：執行 Module F（HR 知識問答）
"""

import requests
import streamlit as st

API_URL = "http://localhost:8000/api/v1/run-agent"

# ── 頁面設定 ─────────────────────────────────────────────────

st.set_page_config(page_title="AI 招募助手", page_icon="🤖", layout="wide")
st.title("🤖 AI 招募助手")
st.caption("用自然語言描述招募需求，AI 自動分析並產出整合報告")

# ── 側邊欄：精簡版，只放 JD 輸入 ───────────────────────────

with st.sidebar:
    st.header("📋 招募資料")
    st.caption("填寫後在右側輸入需求，其餘資訊可直接寫在 Prompt 裡")

    job_title = st.text_input("職稱（選填）", placeholder="例：資深後端工程師")

    jd_text = st.text_area(
        "JD 文字（選填）",
        placeholder=(
            "貼上完整職缺描述...\n\n"
            "💡 也可以直接把 JD 貼在右側的 Prompt 裡，效果相同"
        ),
        height=300,
    )

    st.markdown("---")
    st.caption(
        "ℹ️ v1.7 起，公司名稱、文化關鍵字、薪資範圍等資訊\n"
        "**不需要在此填寫**，直接寫在 Prompt 裡即可，\n"
        "AI 會自動辨識並套用到分析中。"
    )

# ── 主畫面：提示說明 + 對話區 ────────────────────────────────

# 提示說明區（可收合）
with st.expander("💡 這個助手能做什麼？怎麼寫 Prompt？", expanded=True):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
#### 🎯 可以幫你做的事

| 功能 | 說明 |
|------|------|
| **JD 改寫** | 提供三種風格版本（Startup / 穩定企業 / 高成長），並標示推薦版本 |
| **薪資競爭力分析** | 對比市場薪資資料，評估你的方案是否具競爭力 |
| **Sourcing 管道建議** | 推薦適合的人才招募渠道與策略 |
| **HR 知識問答** | 回答勞基法、離職、請假、試用期等 HR 相關問題（不需要 JD） |
| **一次全跑** | 同時執行以上多個功能，產出完整招募建議報告 |
        """)

    with col2:
        st.markdown("""
#### ✍️ 怎麼寫 Prompt？

**可以在 Prompt 裡提供的資訊：**
- 公司名稱、願景、文化關鍵字
- 產業背景、管理風格、語氣偏好
- 薪資預算範圍（例：月薪 6-8 萬）
- 公司類型（新創 / 外商 / 大型企業）
- 職級（Junior / Senior / Manager）

**範例 Prompt：**
```
幫我改寫以下這份 JD，並分析薪資競爭力。
公司是台積電，文化是創新與嚴謹，屬於大型企業，
薪資預算月薪 8-12 萬，職級 Senior。

[在這裡貼上 JD 內容]
```

```
幫我改寫 JD 並推薦 sourcing 管道。
公司：AppWorks 新創，願景是賦能亞洲新創，
文化關鍵字：開放、快速迭代、扁平。

[貼上 JD]
```

```
勞基法規定試用期最長可以幾個月？
可以在試用期內無預告解雇嗎？
```
        """)

st.markdown("---")

# ── 對話紀錄初始化 ────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

# 顯示歷史對話
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── 使用者輸入 ────────────────────────────────────────────────

user_input = st.chat_input(
    "輸入招募需求（可包含 JD、公司資料、薪資預算等）或直接問 HR 問題..."
)

if user_input:
    # 顯示使用者訊息
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # v1.7：前端只傳 user_input、job_title、jd_text（如有填寫）
    # company_profile 欄位改由 parse_input_node 從 user_input 自動抽取
    payload = {
        "user_input": user_input,
        "job_title": job_title or None,
        "jd_text": jd_text or None,
        "company_profile": None,  # 由 parse_input_node 負責
    }

    # 呼叫 API
    with st.chat_message("assistant"):
        with st.spinner("Agent 分析中，請稍候..."):
            try:
                response = requests.post(API_URL, json=payload, timeout=120)
                response.raise_for_status()
                data = response.json()

                final_report   = data.get("final_report", "")
                steps_taken    = data.get("steps_taken", [])
                error_messages = data.get("error_messages", [])

                # 顯示執行路徑（clarify 時顯示特別提示）
                if steps_taken:
                    if steps_taken == ["clarify"]:
                        st.caption("🤔 需要補充資訊")
                    else:
                        steps_display = " → ".join(steps_taken)
                        st.caption(f"✅ 執行模組：{steps_display}")

                # 顯示錯誤訊息（若有）
                if error_messages:
                    with st.expander("⚠️ 執行過程中的警告訊息", expanded=False):
                        for err in error_messages:
                            st.warning(err)

                # 顯示最終報告（包含 clarification 提問）
                st.markdown(final_report)

                # 儲存 assistant 訊息
                steps_label = " → ".join(steps_taken) if steps_taken else ""
                assistant_content = (
                    f"✅ 執行模組：{steps_label}\n\n{final_report}"
                    if steps_label and steps_taken != ["clarify"]
                    else final_report
                )
                st.session_state.messages.append(
                    {"role": "assistant", "content": assistant_content}
                )

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