"""
Module C：Salary Competitiveness Detector
從 session_state 帶入 Module A（job_title、company_type、industry、seniority_level）
與 Module B（job_description_text）、Module D（education_preference）
HR 不需額外填寫任何欄位，直接送出即可取得薪資競爭力分析。
"""

import streamlit as st
import requests


# ── 強制流程順序 ──────────────────────────────────────────
# Module C 需要 Module A 的基本職缺資料、 Module B 的 JD 文字、 Module D 的學經歷資料
if not st.session_state.get("module_a_result"):
    st.warning("⚠️ 請先完成「JD 分析」再繼續。")
    st.stop()

if not st.session_state.get("module_b_result"):
    st.warning("⚠️ 請先完成「JD 改寫」再繼續。")
    st.stop()

if not st.session_state.get("module_d_result"):
    st.warning("⚠️ 請先完成「候選人 Persona」再繼續。")
    st.stop()


st.title("💰 薪資競爭力分析")
st.markdown("根據職缺資料與政府統計數據，評估 JD 薪資的市場競爭力。")
st.markdown("---")


# ── 從 session_state 取出上游資料 ────────────────────────
job_title = st.session_state.get("job_title", "")
company_type = st.session_state.get("company_type")
industry = st.session_state.get("industry")
seniority_level = st.session_state.get("seniority_level")

# Module B 的 JD 文字：優先用 HR 選定的改寫版本，沒有則用原始 JD
selected_jd = st.session_state.get("selected_jd")
original_jd = st.session_state.get("original_jd", "")
job_description_text = selected_jd if selected_jd else original_jd

# Module D 的學歷條件（選填）
education_preference = st.session_state.get("education_preference")
education_level = education_preference.get("level") if education_preference else None
salary_min = st.session_state.get("salary_min")
salary_max = st.session_state.get("salary_max")


# ── 確認帶入的資料 ────────────────────────────────────────
with st.expander("📋 本次分析使用的資料（展開確認）"):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**職稱：** {job_title or '（未提供）'}")
        st.markdown(f"**產業：** {industry or '（未提供）'}")
        st.markdown(f"**公司規模：** {company_type or '（未提供）'}")
    with col2:
        st.markdown(f"**年資層級：** {seniority_level or '（未提供）'}")
        st.markdown(f"**學歷要求：** {education_level or '（未提供）'}")
        jd_source = "改寫後 JD" if selected_jd else "原始 JD"
        st.markdown(f"**JD 來源：** {jd_source}")
        st.markdown(f"**薪資範圍：** {f'{salary_min:,}–{salary_max:,} 元／月' if salary_min and salary_max else salary_min and f'{salary_min:,} 元／月起' or '（未填）'}")

    st.markdown("**JD 文字（前 200 字）：**")
    st.caption(job_description_text[:200] + "..." if len(job_description_text) > 200 else job_description_text)

st.markdown("---")


# ── 送出按鈕 ──────────────────────────────────────────────
if st.button("🔍 分析薪資競爭力", type="primary", use_container_width=True):
    with st.spinner("AI 分析薪資競爭力中，請稍候..."):
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/check-salary",
                json={
                    "job_title": job_title,
                    "company_type": company_type,
                    "industry": industry,
                    "seniority_level": seniority_level,
                    "job_description_text": job_description_text,
                    "education_level": education_level,
                    "salary_min": salary_min, 
                    "salary_max": salary_max   
                },
                timeout=60,
            )

            if response.status_code == 200:
                result = response.json()
                st.session_state["module_c_result"] = result
                st.success("✅ 薪資競爭力分析完成！")
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
if st.session_state.get("module_c_result"):
    result = st.session_state["module_c_result"]
    salary_range = result.get("market_salary_range", {})

    st.markdown("---")

    # ── 1. 市場薪資區間 ───────────────────────────────────
    st.markdown("### 📊 市場薪資參考區間")
    st.caption("資料來源：勞動部職類別薪資調查（114年）× 主計總處薪資統計（113年）")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="P25（市場偏低基準）",
            value=f"${salary_range.get('p25_monthly', 0):,}",
            help="市場上 25% 的人月薪低於此值"
        )
    with col2:
        st.metric(
            label="中位數",
            value=f"${salary_range.get('median_monthly', 0):,}",
            help="市場薪資中位數"
        )
    with col3:
        st.metric(
            label="P75（市場競爭基準）",
            value=f"${salary_range.get('p75_monthly', 0):,}",
            help="市場上 75% 的人月薪低於此值，高於此值代表薪資具競爭力"
        )

    st.markdown("---")

    # ── 2. 競爭力等級 ─────────────────────────────────────
    st.markdown("### 🎯 薪資競爭力判斷")

    level = result.get("competitiveness_level", "")

    # 依等級顯示對應顏色
    level_color = {
        "高度競爭": "🟢",
        "具競爭力": "🔵",
        "普通":    "🟡",
        "偏低":    "🟠",
        "明顯偏低": "🔴",
    }
    icon = level_color.get(level, "⚪")
    st.markdown(f"## {icon} {level}")
    st.markdown(result.get("competitiveness_reason", ""))

    st.markdown("---")

    # ── 3. 薪資建議 ───────────────────────────────────────
    st.markdown("### 💡 薪資建議")
    st.info(result.get("salary_suggestion", ""))

    st.markdown("---")

    # ── 4. 可信度 ─────────────────────────────────────────
    st.markdown("### 🔬 推估可信度")

    confidence = result.get("confidence_level", "")
    confidence_display = {
        "high":   "🟢 高（職稱與產業均能精確對應官方分類）",
        "medium": "🟡 中（部分欄位需模糊映射，結果僅供參考）",
        "low":    "🔴 低（職稱或產業無法對應，僅能提供概估）",
    }
    st.markdown(confidence_display.get(confidence, confidence))
    st.caption(result.get("confidence_reason", ""))

    st.markdown("---")

    # ── 5. 資料來源 ───────────────────────────────────────
    with st.expander("📎 本次推估引用的資料來源"):
        st.markdown(result.get("data_sources", ""))

    # ── 6. Disclaimer ─────────────────────────────────────
    st.caption(f"⚠️ {result.get('disclaimer', '')}")
    
    st.markdown("---")
    if not st.session_state.get("module_e_result"):
        st.success("✅ 薪資分析完成！如需生成搜尋語法，請前往左側選單的「Sourcing 助手」繼續。")
    else:
        st.success("✅ 薪資分析完成！完整流程已走完。")