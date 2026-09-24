"""
Module F：HR 知識助手
Chat UI — 使用者輸入問題，呼叫 POST /api/v1/copilot/query，
顯示 AI 回答並標示使用的 Tool。
"""

import os

import streamlit as st
import requests

# 後端 API 位址：本地開發預設 localhost:8000，部署到 Railway 時由環境變數 API_BASE_URL 覆蓋
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


# ── Tool 標籤對應 ──────────────────────────────────────────
_TOOL_LABEL = {
    "rag_search":       "📚 知識庫",
    "lookup_employee":  "👤 員工資料",
    "calculate_leave":  "📅 假別計算",
    "none":             "—",
}


# ── 頁面設定 ───────────────────────────────────────────────
st.title("🤖 HR 知識助手")
st.markdown("詢問勞基法規定、公司政策，或查詢員工假別、基本資料。")
st.markdown("---")

# ── 使用說明（可折疊）─────────────────────────────────────
with st.expander("💡 可以問什麼？"):
    st.markdown(
        """
        **勞基法 / 公司政策**
        - 試用期最長幾個月？
        - 資遣費怎麼計算？
        - 員工推薦獎金是多少？

        **員工基本資料**
        - 王大明的部門是什麼？
        - 查詢工號 10003 的資料

        **假別與餘額**
        - 王大明還有幾天特休？
        - 工號 10002 的假別使用情況
        """
    )

# ── 初始化對話紀錄 ─────────────────────────────────────────
# session_state["copilot_messages"] 儲存整段對話，格式：
# [{"role": "user"|"assistant", "content": str, "tool_used": str|None}]
if "copilot_messages" not in st.session_state:
    st.session_state["copilot_messages"] = []

# ── 顯示歷史對話 ───────────────────────────────────────────
for msg in st.session_state["copilot_messages"]:
    with st.chat_message(msg["role"]):
        # 三個工具統一格式，一律用 st.markdown()
        st.markdown(msg["content"])
        # 助手回應才顯示 Tool 標籤
        if msg["role"] == "assistant" and msg.get("tool_used"):
            label = _TOOL_LABEL.get(msg["tool_used"], msg["tool_used"])
            st.caption(f"資料來源：{label}")

# ── 使用者輸入 ─────────────────────────────────────────────
# st.chat_input() 固定在頁面底部，按 Enter 送出
question = st.chat_input("請輸入問題，例：王大明還有幾天特休？")

if question:
    # 1. 立即顯示使用者訊息
    st.session_state["copilot_messages"].append(
        {"role": "user", "content": question, "tool_used": None}
    )
    with st.chat_message("user"):
        st.markdown(question)

    # 2. 呼叫後端 API
    with st.chat_message("assistant"):
        with st.spinner("查詢中..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/copilot/query",
                    json={"question": question},
                    timeout=30,
                )

                if response.status_code == 200:
                    data = response.json()
                    answer   = data["answer"]
                    tool_used = data["tool_used"]
                else:
                    answer    = f"API 錯誤（{response.status_code}）：{response.text}"
                    tool_used = "none"

            except requests.exceptions.ConnectionError:
                answer    = "⚠️ 無法連接後端，請確認 FastAPI 伺服器已啟動。\n\n```\nuvicorn app.main:app --reload\n```"
                tool_used = "none"
            except requests.exceptions.Timeout:
                answer    = "⚠️ 請求逾時，請稍後再試。"
                tool_used = "none"

        # 3. 顯示回答與 Tool 標籤
        # 三個工具統一輸出格式：「結論 + 分隔線 + 卡片」，一律用 st.markdown() 渲染
        st.markdown(answer)
        label = _TOOL_LABEL.get(tool_used, tool_used)
        st.caption(f"資料來源：{label}")

    # 4. 存入對話紀錄
    st.session_state["copilot_messages"].append(
        {"role": "assistant", "content": answer, "tool_used": tool_used}
    )

# ── 清除對話按鈕 ───────────────────────────────────────────
if st.session_state["copilot_messages"]:
    st.markdown("---")
    if st.button("🗑️ 清除對話紀錄", use_container_width=True):
        st.session_state["copilot_messages"] = []
        st.rerun()