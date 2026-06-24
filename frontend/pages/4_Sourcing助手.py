"""
Module E：AI Sourcing Assistant
從 session_state 帶入 Module D 的 Persona 結果
HR 只需選填 additional_keywords 與 exclude_keywords
輸出：職稱同義展開、Boolean search string（五種語法）、Outreach 訊息、Sourcing Tips
"""

import streamlit as st
import requests


# ── 強制流程順序 ──────────────────────────────────────────
if not st.session_state.get("module_d_result"):
    st.warning("⚠️ 請先完成「候選人 Persona」再繼續。")
    st.stop()

st.title("🔍 Sourcing 助手")
st.markdown("根據候選人 Persona，AI 自動生成搜尋語法與主動聯繫訊息。")
st.markdown("---")

# ── 從 session_state 取出 Module D 的結果 ────────────────
d_result = st.session_state["module_d_result"]
persona = d_result.get("persona", {})
job_title = st.session_state.get("job_title", "")

# ── 確認帶入的 Persona 資料 ───────────────────────────────
with st.expander("📋 從 Module D 帶入的資料（展開確認）"):
    st.markdown(f"**職稱：** {job_title}")
    st.markdown(f"**理想年資：** {persona.get('ideal_seniority', '（未提供）')}")

    st.markdown("**核心技能：**")
    skills = persona.get("key_skills", [])
    if skills:
        st.markdown(" ".join([f"`{s}`" for s in skills]))

    st.markdown("**常出現的平台：**")
    for ch in persona.get("likely_channels", []):
        st.markdown(f"- {ch}")

    st.markdown("**溝通偏好：**")
    st.markdown(persona.get("preferred_message_style", "（未提供）"))

    edu = st.session_state.get("education_preference")
    if edu:
        edu_display = edu["level"]
        if edu.get("notes"):
            edu_display += f"（{edu['notes']}）"
        st.markdown(f"**學歷條件：** {edu_display}")

st.markdown("---")

# ── HR 選填補充 ───────────────────────────────────────────
st.markdown("### ⚙️ 補充關鍵字（選填）")
st.markdown("系統已從 Persona 自動帶入核心技能，你可以額外補充或排除特定詞彙。")

col1, col2 = st.columns(2)
with col1:
    additional_input = st.text_input(
        "額外關鍵字",
        placeholder="例：Docker、AWS（用逗號分隔）"
    )
with col2:
    exclude_input = st.text_input(
        "排除詞彙",
        placeholder="例：manager、director（用逗號分隔）"
    )

st.markdown("---")

# ── 送出按鈕 ──────────────────────────────────────────────
if st.button("🚀 生成 Sourcing 內容", type="primary", use_container_width=True):

    additional_keywords = [k.strip() for k in additional_input.split(",") if k.strip()] if additional_input else []
    exclude_keywords = [k.strip() for k in exclude_input.split(",") if k.strip()] if exclude_input else []

    with st.spinner("AI 生成 Sourcing 內容中，請稍候..."):
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/generate-sourcing",
                json={
                    "job_title": job_title,
                    "key_skills": persona.get("key_skills", []),
                    "ideal_seniority": persona.get("ideal_seniority", ""),
                    "likely_channels": persona.get("likely_channels", []),
                    "likely_background": persona.get("likely_background", []),
                    "candidate_motivators": persona.get("candidate_motivators", []),
                    "likely_concerns": persona.get("likely_concerns", []),
                    "preferred_message_style": persona.get("preferred_message_style", ""),
                    "education_preference": st.session_state.get("education_preference"),
                    "additional_keywords": additional_keywords,
                    "exclude_keywords": exclude_keywords,
                },
                timeout=60,
            )

            if response.status_code == 200:
                result = response.json()
                st.session_state["module_e_result"] = result
                st.success("✅ Sourcing 內容生成完成！")
            else:
                st.error(f"API 錯誤：{response.status_code}")
                st.json(response.json())

        except requests.exceptions.ConnectionError:
            st.error("無法連接後端，請確認 FastAPI 伺服器已啟動")
        except requests.exceptions.Timeout:
            st.error("請求逾時，請稍後再試")
        except Exception as e:
            st.error(f"發生未預期的錯誤：{e}")

# ── 結果顯示區 ────────────────────────────────────────────
if st.session_state.get("module_e_result"):
    result = st.session_state["module_e_result"]

    st.markdown("---")

    # ── 1. 職稱同義展開 ──────────────────────────────────
    st.markdown("### 📌 職稱同義展開")
    st.markdown("以下職稱將用於組裝 Boolean search string：")
    expanded = result.get("expanded_titles", [])
    if expanded:
        st.markdown(" ".join([f"`{t}`" for t in expanded]))

    st.markdown("---")

    # ── 2. Boolean Search String ─────────────────────────
    st.markdown("### 🔎 Boolean Search String")

    # 區塊一：LinkedIn
    st.markdown("#### LinkedIn")
    st.caption("LinkedIn 內建搜尋需登入帳號；Google X-Ray 為免費替代方案，透過 Google 搜尋 LinkedIn 公開頁面。")
    tab_li, tab_google_li = st.tabs(["LinkedIn 內建", "Google X-Ray - LinkedIn"])
    with tab_li:
        st.code(result.get("boolean_string_linkedin", ""), language=None)
    with tab_google_li:
        st.code(result.get("boolean_string_google_linkedin", ""), language=None)

    st.markdown("---")

    # 區塊二：CakeResume
    st.markdown("#### CakeResume")
    st.caption("CakeResume 內建搜尋需登入帳號；Google X-Ray 為免費替代方案，透過 Google 搜尋 CakeResume 公開履歷。")
    tab_cake, tab_google_cake = st.tabs(["CakeResume 內建", "Google X-Ray - CakeResume"])
    with tab_cake:
        st.code(result.get("boolean_string_cake", ""), language=None)
    with tab_google_cake:
        st.code(result.get("boolean_string_google_cake", ""), language=None)

    st.markdown("---")

    # 區塊三：104
    st.markdown("#### 104 人力銀行")
    st.warning("⚠️ 104 主動搜尋候選人履歷需企業付費帳號（104 人資網）。無付費帳號者可使用下方 Google X-Ray 語法搜尋 104 公開頁面。")
    tab_google_104, = st.tabs(["Google X-Ray - 104"])
    with tab_google_104:
        st.code(result.get("boolean_string_google_104", ""), language=None)

    st.markdown("---")

    # ── 3. Outreach 訊息（可編輯）────────────────────────
    st.markdown("### ✉️ 破冰聯繫訊息草稿")
    st.markdown("AI 根據候選人溝通偏好生成，可用於 LinkedIn、CakeResume 或任何訊息管道，直接在下方編輯後複製使用。")
    st.text_area(
        "outreach_message",
        value=result.get("outreach_message_template", ""),
        height=200,
        label_visibility="collapsed"
    )

    st.markdown("---")

    # ── 4. Sourcing Tips ──────────────────────────────────
    st.markdown("### 💡 Sourcing 建議")
    tips = result.get("sourcing_tips", [])
    if tips:
        for tip in tips:
            st.markdown(f"- {tip}")

    st.markdown("---")
    st.success("✅ A → B → D → E 完整流程已走完。")