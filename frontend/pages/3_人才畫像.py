import streamlit as st
import requests


"""
Module D：Candidate Persona Generator
從 session_state 帶入 Module A + B 的所有結果
使用者不需要重複填寫任何資訊
"""
# ── 強制流程順序：必須先完成 Module A 和 B 才能進入此頁 ────────────
if not st.session_state.get("module_a_result"):
    st.warning("⚠️ 請先完成「JD 分析」再繼續。")
    st.stop()

if not st.session_state.get("module_b_result"):
    st.warning("⚠️ 請先完成「JD 改寫」並選擇一個版本再繼續。")
    st.stop()


st.title("👤 候選人 Persona")
st.markdown("根據選定的 JD 版本，AI 反推理想候選人的樣貌。")
st.markdown("---")

# ── 確認前置資料是否齊全 ──────────────────────────────────
ready = True

# 檢查 selected_jd（從 Module B 選定的版本）
if not st.session_state.get("selected_jd"):
    st.warning("⚠️ 尚未選擇 JD 版本，請先完成「JD 改寫」並選擇一個版本。")
    ready = False
else:
    st.markdown("### 📄 已選定的 JD 版本")
    st.text_area(
        "selected_jd",
        value=st.session_state["selected_jd"],
        height=150,
        disabled=True,
        label_visibility="collapsed"
    )

# 檢查 company_profile（從 Module B 帶入）
if not st.session_state.get("company_profile"):
    st.warning("⚠️ 尚未填寫 Company Profile，請先完成「JD 改寫」。")
    ready = False


st.markdown("---")

# ── 送出按鈕 ──────────────────────────────────────────────
if st.button(
    "🔮 生成候選人 Persona",
    type="primary",
    use_container_width=True,
    disabled=not ready
):
    with st.spinner("AI 分析理想候選人中..."):
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/generate-persona",
                json={
                    # 從 Module A 帶入：職稱與三個選填欄位
                    # 這四個都是使用者輸入的資料，在 1_JD分析.py 送出成功後獨立存進 session_state
                    # 不從 module_a_result 讀，因為 AnalyzeJDResponse 只有分析結果，沒有輸入欄位
                    "job_title": st.session_state.get("job_title", ""),
                    "company_type": st.session_state.get("company_type"),
                    "industry": st.session_state.get("industry"),
                    "seniority_level": st.session_state.get("seniority_level"),
                    # 從 Module B 帶入：選定的 JD 版本、Company Profile、目標候選人特質
                    # 這三個在 2_JD改寫.py 送出成功後存進 session_state
                    "job_description_text": st.session_state["selected_jd"],
                    "company_profile": st.session_state["company_profile"],
                    "target_candidate_focus": st.session_state.get("target_candidate_focus"),
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

    # 結果被包在 persona 這一層裡，要先取出來
    persona = result.get("persona", {})

    st.markdown("## 🎯 理想候選人 Persona")

    # ── 本次分析使用的資料（expander 收起，需要確認時才展開）──
    with st.expander("📋 本次分析使用的資料（展開確認）"):

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**從 Module A 帶入**")
            st.markdown(f"- 職稱：{st.session_state.get('job_title', '（未填）')}")

            # 公司類型、產業、資歷層級從獨立的 session_state key 讀取
            # 不從 module_a_result 讀，因為這三個是輸入欄位（AnalyzeJDRequest）
            # 不是後端分析結果（AnalyzeJDResponse），所以 module_a_result 裡找不到
            st.markdown(f"- 公司類型：{st.session_state.get('company_type') or '（未填）'}")
            st.markdown(f"- 產業：{st.session_state.get('industry') or '（未填）'}")
            st.markdown(f"- 資歷層級：{st.session_state.get('seniority_level') or '（未填）'}")

        with col2:
            st.markdown("**從 Module B 帶入**")

            # company_profile 是巢狀字典，逐欄位顯示
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

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        # 理想年資是短文字，適合用 metric 顯示
        st.metric("理想年資", persona.get("ideal_seniority", "-"))
    with col2:
        # 建議溝通語氣可能是長句子，改用一般文字顯示避免截斷
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
    st.success("✅ Phase 1 三個核心模組全部完成！")