"""
Module B：JD Rewrite AI
讓使用者填寫 Company Profile，呼叫後端 API，顯示三種改寫版本
"""


import streamlit as st
import requests
import re


# ── 強制流程順序：必須先完成 Module A 才能進入此頁 ────────
if not st.session_state.get("module_a_result"):
    st.warning("⚠️ 請先完成「JD 分析」再進行改寫。")
    st.stop()


st.title("✍️ JD 改寫")
st.markdown("根據你的公司文化，AI 產出三種風格的改寫版本。")
st.markdown("---")

# ── 原始 JD（從 session_state 帶入，不需要重新貼）────────
st.markdown("### 📄 原始 JD")

# original_jd 一定從 Module A 帶入
# 上方已用 st.stop() 確保 Module A 一定跑過
original_jd = st.text_area(
    "原始 JD",
    value=st.session_state["original_jd"],
    height=150,
    disabled=True,
    label_visibility="collapsed"
)

st.markdown("---")

# ── Company Profile 輸入區 ────────────────────────────────
st.markdown("### 🏢 Company Profile")
st.markdown("告訴 AI 你的公司是什麼樣的，改寫結果才會有公司個性。")

col1, col2 = st.columns(2)
with col1:
    company_name = st.text_input(
        "公司名稱 *",
        placeholder="例：Acme SaaS"
    )
with col2:
    vision = st.text_input(
        "公司願景 *",
        placeholder="例：打造亞洲最好的 B2B SaaS 平台"
    )

# 說明文字明確列出支援的分隔符號
culture_keywords_input = st.text_input(
    "企業文化關鍵字 *（可用逗號、頓號、空白、分號、斜線分隔）",
    placeholder="例：透明、扁平、快速迭代"
)

st.markdown("---")

with st.expander("⚙️ 進階設定（選填）"):
    col1, col2 = st.columns(2)
    with col1:
        manager_style = st.text_input(
            "主管風格",
            placeholder="例：重視自主性、鼓勵實驗"
        )
        tone_preference = st.selectbox(
            "語氣偏好",
            options=["", "formal", "casual", "energetic", "professional"],
            format_func=lambda x: "請選擇" if x == "" else x
        )
    with col2:
        must_include_input = st.text_input(
            "必須帶到的訊息（可用逗號、頓號、空白、分號、斜線分隔）",
            placeholder="例：技術決策權、彈性工時"
        )
        must_avoid_input = st.text_input(
            "絕對不能出現的詞（可用逗號、頓號、空白、分號、斜線分隔）",
            placeholder="例：抗壓、配合加班"
        )
    industry_context = st.text_input(
        "產業背景補充",
        placeholder="例：B2B SaaS 新創、A 輪階段"
    )

target_candidate_focus = st.text_input(
    "想吸引的候選人特質（選填）",
    placeholder="例：喜歡挑戰、重視技術成長的工程師"
)

st.markdown("---")

# ── 送出按鈕 ──────────────────────────────────────────────
if st.button("✨ 產出改寫版本", type="primary", use_container_width=True):

    if not original_jd:
        st.warning("請提供原始 JD")
    elif not company_name or not vision or not culture_keywords_input:
        st.warning("請填寫公司名稱、公司願景、企業文化關鍵字")
    else:
        # 統一的分隔符號規則：逗號、中文逗號、頓號、分號、中文分號、斜線、空白
        # 套用在所有需要切割的欄位上
        split_pattern = r"[,，、；;/\s]+"

        culture_keywords = [k.strip() for k in re.split(split_pattern, culture_keywords_input) if k.strip()]
        must_include = [k.strip() for k in re.split(split_pattern, must_include_input) if k.strip()] if must_include_input else []
        must_avoid = [k.strip() for k in re.split(split_pattern, must_avoid_input) if k.strip()] if must_avoid_input else []

        company_profile = {
            "company_name": company_name,
            "culture_keywords": culture_keywords,
            "vision": vision,
            "manager_style": manager_style if manager_style else None,
            "tone_preference": tone_preference if tone_preference else None,
            "must_include": must_include,   # 空 list [] 就傳 []，不轉成 None
            "must_avoid": must_avoid,      # 空 list [] 就傳 []，不轉成 None
            "industry_context": industry_context if industry_context else None,
        }
        st.session_state["company_profile"] = company_profile

        with st.spinner("AI 改寫中，請稍候..."):
            try:
                response = requests.post(
                    "http://localhost:8000/api/v1/rewrite-jd",
                    json={
                        "original_jd": original_jd,
                        "company_profile": company_profile,
                        "target_candidate_focus": target_candidate_focus if target_candidate_focus else None,
                    },
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()
                    st.session_state["module_b_result"] = result
                    # target_candidate_focus 不在 company_profile 裡，需要獨立存
                    st.session_state["target_candidate_focus"] = target_candidate_focus if target_candidate_focus else None
                    st.success("改寫完成！")
                else:
                    # 暫時改成這樣，顯示完整錯誤內容
                    st.error(f"API 錯誤：{response.status_code}")
                    st.json(response.json())   # 把後端回傳的錯誤詳細內容顯示出來

            except requests.exceptions.ConnectionError:
                st.error("無法連接後端，請確認 FastAPI 伺服器已啟動")
            except requests.exceptions.Timeout:
                st.error("請求逾時，請稍後再試")
            except Exception as e:
                st.error(f"發生未預期的錯誤：{e}")

# ── 結果顯示區 ────────────────────────────────────────────
if st.session_state["module_b_result"]:
    result = st.session_state["module_b_result"]

    st.markdown("## 📝 三種改寫版本")
    st.markdown("選擇最符合你公司風格的版本，帶入下一步的人才 Persona 分析。")

    tab1, tab2, tab3 = st.tabs(["🚀 Startup 風", "🏢 穩定企業風", "📈 高成長挑戰型"])

    with tab1:
        st.markdown(result["startup_version"])
        st.markdown("---")
        if st.button("✅ 選擇這個版本", key="btn_startup", use_container_width=True):
            st.session_state["selected_jd"] = result["startup_version"]
            st.success("已選擇 Startup 風！請前往「候選人 Persona」繼續。")

    with tab2:
        st.markdown(result["stable_enterprise_version"])
        st.markdown("---")
        if st.button("✅ 選擇這個版本", key="btn_stable", use_container_width=True):
            st.session_state["selected_jd"] = result["stable_enterprise_version"]
            st.success("已選擇穩定企業風！請前往「候選人 Persona」繼續。")

    with tab3:
        st.markdown(result["high_growth_version"])
        st.markdown("---")
        if st.button("✅ 選擇這個版本", key="btn_high", use_container_width=True):
            st.session_state["selected_jd"] = result["high_growth_version"]
            st.success("已選擇高成長挑戰型！請前往「候選人 Persona」繼續。")

    if result.get("rewrite_notes"): # 如果 rewrite_notes 存在，就顯示改寫重點說明
        st.markdown("---")
        st.markdown("### 📌 改寫重點說明")
        for note in result["rewrite_notes"]:
            st.markdown(f"- {note}")

    st.markdown("---")
    st.success("✅ 選定版本後，請前往左側選單的「候選人 Persona」繼續下一步。")