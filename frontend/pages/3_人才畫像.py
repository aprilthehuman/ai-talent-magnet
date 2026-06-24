"""
Module D：Candidate Persona Generator
從 session_state 帶入 Module A + B 的所有結果
使用者不需要重複填寫任何資訊
新增：education_preference 學歷參考條件（選填），存進 session_state 供 Module E 使用
"""


import streamlit as st
import requests


# ── 強制流程順序：必須先完成 Module A 和 B 才能進入此頁 ────────────
if not st.session_state.get("module_a_result"):
    st.warning("⚠️ 請先完成「JD 分析」再繼續。")
    st.stop()

if not st.session_state.get("selected_jd"):
    st.warning("⚠️ 請先完成「JD 改寫」並選擇一個版本再繼續。")
    st.stop()

st.title("👤 候選人 Persona")
st.markdown("根據選定的 JD 版本，AI 反推理想候選人的樣貌。")
st.markdown("---")

# ── 確認前置資料是否齊全 ──────────────────────────────────
ready = True

st.markdown("### 📄 已選定的 JD 版本")
st.text_area(
    "selected_jd",
    value=st.session_state["selected_jd"],
    height=150,
    disabled=True,
    label_visibility="collapsed"
)

if not st.session_state.get("company_profile"):
    st.warning("⚠️ 尚未填寫 Company Profile，請先完成「JD 改寫」。")
    ready = False

st.markdown("---")

# ── 學歷條件（選填）────────────────────────────────────────
st.markdown("### 🎓 學歷參考條件（選填）")
st.markdown("作為參考條件，影響 Persona 描述與下游 Sourcing 策略。")

edu_level = st.selectbox(
    "學歷要求",
    options=["不限", "大學", "碩士", "博士"],
)
edu_notes = st.text_input(
    "補充說明（選填）",
    placeholder="例：台清交成優先、國外碩士加分"
)

st.markdown("---")

# ── 送出按鈕 ──────────────────────────────────────────────
if st.button(
    "🔮 生成候選人 Persona",
    type="primary",
    use_container_width=True,
    disabled=not ready
):
    # 組裝 education_preference
    # 選「不限」且沒有補充說明時，視為沒有學歷條件，傳 None 給後端
    education_preference = None
    if edu_level != "不限" or edu_notes:
        education_preference = {
            "level": edu_level,
            "notes": edu_notes if edu_notes else None
        }
    st.session_state["education_preference"] = education_preference

    with st.spinner("AI 分析理想候選人中..."):
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/generate-persona",
                json={
                    "job_title": st.session_state.get("job_title", ""),
                    "company_type": st.session_state.get("company_type"),
                    "industry": st.session_state.get("industry"),
                    "seniority_level": st.session_state.get("seniority_level"),
                    "job_description_text": st.session_state["selected_jd"],
                    "company_profile": st.session_state["company_profile"],
                    "target_candidate_focus": st.session_state.get("target_candidate_focus"),
                    "education_preference": education_preference,  # ← 新增
                },
                timeout=60,
            )

            if response.status_code == 200:
                result = response.json()
                st.session_state["module_d_result"] = result
                st.success("Persona 生成完成！")
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
if st.session_state.get("module_d_result"):
    result = st.session_state["module_d_result"]
    persona = result.get("persona", {})

    st.markdown("## 🎯 理想候選人 Persona")
    st.markdown(f"**職稱：** {result.get('job_title', '-')}")

    with st.expander("📋 本次分析使用的資料（展開確認）"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**從 Module A 帶入**")
            st.markdown(f"- 職稱：{st.session_state.get('job_title', '（未填）')}")
            st.markdown(f"- 公司類型：{st.session_state.get('company_type') or '（未填）'}")
            st.markdown(f"- 產業：{st.session_state.get('industry') or '（未填）'}")
            st.markdown(f"- 資歷層級：{st.session_state.get('seniority_level') or '（未填）'}")

        with col2:
            st.markdown("**從 Module B 帶入**")
            profile = st.session_state.get("company_profile") or {}
            st.markdown(f"- 公司名稱：{profile.get('company_name', '（未填）')}")
            st.markdown(f"- 公司願景：{profile.get('vision', '（未填）')}")
            st.markdown(f"- 企業文化：{', '.join(profile.get('culture_keywords', []))}")
            st.markdown(f"- 主管風格：{profile.get('manager_style') or '（未填）'}")
            st.markdown(f"- 語氣偏好：{profile.get('tone_preference') or '（未填）'}")
            st.markdown(f"- 必帶訊息：{', '.join(profile.get('must_include', [])) or '（未填）'}")
            st.markdown(f"- 禁用詞：{', '.join(profile.get('must_avoid', [])) or '（未填）'}")
            st.markdown(f"- 產業背景：{profile.get('industry_context') or '（未填）'}")
            st.markdown(f"- 目標候選人特質：{st.session_state.get('target_candidate_focus') or '（未填）'}")

        # 學歷條件獨立顯示
        st.markdown("**HR 補充**")
        edu = st.session_state.get("education_preference")
        if edu:
            edu_display = edu["level"]
            if edu.get("notes"):
                edu_display += f"（{edu['notes']}）"
            st.markdown(f"- 學歷條件：{edu_display}")
        else:
            st.markdown("- 學歷條件：（未填）")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("理想年資", persona.get("ideal_seniority", "-"))
    with col2:
        st.markdown("**建議溝通語氣**")
        st.markdown(persona.get("preferred_message_style", "-"))

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🎓 可能的職涯背景")
        for item in persona.get("likely_background", []):
            st.markdown(f"- {item}")

        st.markdown("### 💪 核心技能")
        skills = persona.get("key_skills", [])
        if skills:
            st.markdown(" ".join([f"`{s}`" for s in skills]))

    with col2:
        st.markdown("### ❤️ 在意的面向")
        for item in persona.get("candidate_motivators", []):
            st.markdown(f"- {item}")

        st.markdown("### 🤔 可能的顧慮")
        for item in persona.get("likely_concerns", []):
            st.markdown(f"- {item}")

    st.markdown("---")

    st.markdown("### 📍 這類人常出現的平台")
    channels = persona.get("likely_channels", [])
    if channels:
        cols = st.columns(len(channels))
        for i, channel in enumerate(channels):
            with cols[i]:
                st.info(channel)

    st.markdown("---")
    st.success("✅ 選定版本後，請前往左側選單的「Sourcing 助手」繼續下一步。")