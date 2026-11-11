"""
Module A：JD Attraction Analyzer
讓使用者輸入 JD，呼叫後端 API，顯示分析結果
"""


import os

import streamlit as st
import requests   # 用來呼叫 FastAPI 後端

# 後端 API 位址：本地開發預設 localhost:8000，部署到 Railway 時由環境變數 API_BASE_URL 覆蓋
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# 扣分規則（顯示分數明細用）
# 注意：這兩個數字要與 app/services/analyzer_service.py 的扣分規則保持一致
NEGATIVE_PENALTY = 5   # 負面詞每個扣 5 分
VAGUE_PENALTY = 3      # 模糊用語每個扣 3 分


# ── 頁面標題 ──────────────────────────────────────────────
st.title("📋 JD 吸引力分析")
st.markdown("貼上你的職缺描述，AI 幫你找出會讓候選人卻步的問題。")

# ── 計分規則說明 ──────────────────────────────────────────
# 用 container(border=True) 做出有框的區塊，跟下面的 st.info 做視覺區隔
with st.container(border=True):
    st.markdown("#### 📐 計分規則")
    st.code("最終分數 = 60 + AI 語氣分（0~40）− 規則扣分", language=None)
    st.markdown(
        """
- **底分 60**：代表一份基本可用的 JD
- **AI 語氣分（0~40）**：AI 從候選人角度評估整體語氣，給 0 到 40 分的印象分
- **規則扣分**：依下方檢查表逐項扣分，**不設上限**
- 最終分數最低 0 分、最高 100 分

**等級：** 優良 80–100 ｜ 普通 60–79 ｜ 偏低 40–59 ｜ 危險 0–39
"""
    )
    
# 提醒使用者哪些內容會影響分數（對應 keyword_dicts.py 的判斷規則）
st.info(
    """
**想拿高分，JD 本文請盡量寫到這四類資訊（缺一類就扣分）：**

- 💰 **薪資**（−10）：寫出「薪資、月薪、年薪、待遇」，或數字加 K，例如 `58K–72K`等
- 📋 **工作內容**（−10）：寫出「負責、工作內容、職責、你將負責」等
- 🌱 **成長機會**（−8）：寫出「成長、學習、發展、培訓、mentor」等
- 🤝 **團隊文化**（−5）：寫出「團隊、文化、氛圍、夥伴」等

**另外要避開這些用語：**

- 負面詞（每個 −5）：抗壓、加班、責任制、獨當一面、配合度高…
- 模糊用語（每個 −3）：其他相關業務、視情況調整、協助主管…

最後還有 AI 依整體語氣給 0–40 分的印象分。
"""
)
st.markdown("---")

# ── 輸入區 ────────────────────────────────────────────────
# st.text_input() 是單行輸入框
# st.text_area() 是多行輸入框，height 控制高度（單位是像素）
# value= 設定預設值，這裡從 session_state 讀取，
# 這樣使用者在其他頁面輸入過的 JD 會自動帶入，不用重複貼
job_title = st.text_input(
    label="職稱",
    placeholder="例：Python Backend Engineer"
)

job_description = st.text_area(
    label="職缺描述（JD）",
    placeholder="把完整的 JD 文字貼在這裡...",
    height=300,
    value=st.session_state["original_jd"]   # 從 session_state 讀取上次的值
)


st.markdown("---")
st.markdown("### 💰 薪資範圍（選填）")
st.markdown("填寫後可在模組 C 進行薪資競爭力分析。")

col1, col2 = st.columns(2)
with col1:
    salary_min = st.number_input(
        "月薪下限（元）",
        min_value=0,
        step=1000,
        value=0,
        help="例：45000"
    )
with col2:
    salary_max = st.number_input(
        "月薪上限（元）",
        min_value=0,
        step=1000,
        value=0,
        help="例：70000"
    )
    
# 薪資欄位說明：提醒使用者這欄不會被模組 A 讀取
st.caption(
    "💡 此欄位供模組 C 使用。若希望 JD 不被扣「未提供薪資」，"
    "請把薪資寫進 JD 本文。"
)


# 進階選項用 expander 收起來，避免頁面太複雜
# 使用者點開才看到，不影響主要流程
with st.expander("⚙️ 進階選項（選填）"):
    # st.columns() 把這三個欄位並排，節省垂直空間
    col1, col2, col3 = st.columns(3)
    with col1:
        company_type = st.selectbox(
            "公司類型",
            options=["", "startup", "SME", "enterprise"],
            # format_func 控制選項的顯示文字
            format_func=lambda x: "請選擇" if x == "" else x
        )
    with col2:
        industry = st.text_input("產業", placeholder="例：SaaS、電商")
    with col3:
        seniority = st.selectbox(
            "資歷層級",
            options=["", "junior", "mid", "senior"],
            format_func=lambda x: "請選擇" if x == "" else x
        )

st.markdown("---")


# ── 送出按鈕 ──────────────────────────────────────────────
# st.button() 回傳 True/False，被點擊時回傳 True
# 整個 if 區塊只有在按鈕被點擊的那次執行才會進入
if st.button("🔍 開始分析", type="primary", use_container_width=True):
    # type="primary" 讓按鈕變藍色主要樣式
    # use_container_width=True 讓按鈕撐滿整個欄寬

    # 基本驗證：兩個必填欄位都要有內容
    if not job_title or not job_description:
        # st.warning() 顯示黃色警告訊息
        st.warning("請填寫職稱和職缺描述")
    else:
        # 把 JD 存進 session_state，讓其他頁面（Module B）可以讀取
        st.session_state["original_jd"] = job_description

        # st.spinner() 在執行期間顯示轉圈動畫，給使用者等待的視覺回饋
        with st.spinner("AI 分析中，請稍候..."):
            try:
                # 呼叫 FastAPI 後端
                # 注意：FastAPI 要先在另一個 terminal 執行才能呼叫
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/analyze-jd",
                    json={
                        "job_title": job_title,
                        "job_description_text": job_description,
                        "company_type": company_type if company_type else None,
                        "industry": industry if industry else None,
                        "seniority_level": seniority if seniority else None,
                        "salary_min": salary_min if salary_min > 0 else None,
                        "salary_max": salary_max if salary_max > 0 else None
                    },
                    timeout=30   # 最多等 30 秒，避免無限等待
                )

                if response.status_code == 200:
                    result = response.json()
                    # 把結果存進 session_state，讓首頁狀態指標更新
                    st.session_state["module_a_result"] = result
                    # 把職稱、三個選填欄位一起存進 session_state (因為不在 AnalyzeJDResponse 輸出裡)，讓 Module D 可以直接帶入
                    st.session_state["job_title"] = job_title
                    st.session_state["company_type"] = company_type if company_type else None
                    st.session_state["industry"] = industry if industry else None
                    st.session_state["seniority_level"] = seniority if seniority else None
                    st.session_state["salary_min"] = salary_min if salary_min > 0 else None
                    st.session_state["salary_max"] = salary_max if salary_max > 0 else None
                    # st.success() 顯示綠色成功訊息
                    st.success("分析完成！")
                    
                    
                else:
                    st.error(f"API 錯誤：{response.status_code}")

            except requests.exceptions.ConnectionError:
                # 後端沒有啟動時會出現這個錯誤
                st.error("無法連接後端，請確認 FastAPI 伺服器已啟動（uvicorn app.main:app --reload）")
            except requests.exceptions.Timeout:
                st.error("請求逾時，請稍後再試")

# ── 結果顯示區 ────────────────────────────────────────────
# 只要 session_state 有資料，不管有沒有按按鈕，都會顯示
# 按鈕負責：呼叫 API、存結果
# 結果區負責：從 session_state 讀結果、顯示結果

if st.session_state["module_a_result"]:
    result = st.session_state["module_a_result"]

    st.markdown("## 📊 分析結果")

    # 分數和等級並排顯示
    col1, col2 = st.columns(2)
    with col1:
        # st.metric() 顯示大數字指標
        st.metric("吸引力分數", f"{result['attraction_score']} 分")
    with col2:
        st.metric("等級", result["score_label"])

    st.markdown("---")

    # ── 分數計算明細 ───────────────────────────────────────
    st.markdown("### 🧮 分數是怎麼算出來的")
 
    neg_list = result["negative_keywords_detected"]
    vague_list = result["vague_phrases_detected"]
    missing_list = result["missing_elements"]
    tone_score = result.get("tone_score")   # 舊結果可能沒有這個欄位
 
    # 各類扣分小計
    neg_total = len(neg_list) * NEGATIVE_PENALTY
    vague_total = len(vague_list) * VAGUE_PENALTY
    missing_total = sum(item["penalty"] for item in missing_list)
    total_deduction = neg_total + vague_total + missing_total
 
    if tone_score is None:
        st.info("此結果缺少 AI 語氣分，請重新按一次「開始分析」。")
    else:
        # 用 Markdown 表格逐列組出來：加分在上、扣分在下、合計在最後
        rows = [
            "| 項目 | 內容 | 分數 |",
            "|---|---|---:|",
            "| 底分 | 一份基本可用的 JD | +60 |",
            f"| AI 語氣分 | 0–40 分，AI 評估整體語氣 | +{tone_score} |",
        ]
        if neg_list:
            rows.append(
                f"| 負面詞 × {len(neg_list)} | {'、'.join(neg_list)}（每個 −{NEGATIVE_PENALTY}） | −{neg_total} |"
            )
        if vague_list:
            rows.append(
                f"| 模糊用語 × {len(vague_list)} | {'、'.join(vague_list)}（每個 −{VAGUE_PENALTY}） | −{vague_total} |"
            )
        for item in missing_list:
            rows.append(f"| 缺失資訊 | {item['label']} | −{item['penalty']} |")
        if total_deduction == 0:
            rows.append("| 規則扣分 | ✅ 沒有扣分項目 | 0 |")
 
        raw_score = 60 + tone_score - total_deduction
        rows.append(
            f"| **合計** | 60 + {tone_score} − {total_deduction} | **{raw_score}** |"
        )
        st.markdown("\n".join(rows))
 
        # 算出來超出 0–100 時，提醒使用者最終分數被夾住
        if raw_score != result["attraction_score"]:
            st.caption(
                f"⚠️ 計算結果為 {raw_score}，超出 0–100 範圍，"
                f"最終分數取 {result['attraction_score']}。"
            )
 
    st.markdown("---")
 
    # AI 語氣評語（文字說明；分數在上方明細表）
    st.markdown("### 🎯 AI 語氣評語")
    # st.info() 顯示藍色資訊框，適合放重要說明文字
    st.info(result["tone_analysis"])
 
    # 負面詞彙和模糊用語並排
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ⚠️ 偵測到的負面詞彙")
        if neg_list:
            for kw in neg_list:
                # st.markdown() 搭配 emoji 做成簡單的清單
                st.markdown(f"- 🔴 {kw}")
        else:
            st.markdown("✅ 無負面詞彙")
 
    with col2:
        st.markdown("### 💬 模糊用語")
        if vague_list:
            for phrase in vague_list:
                st.markdown(f"- 🟡 {phrase}")
        else:
            st.markdown("✅ 無模糊用語")
 
    st.markdown("---")
 
    # 缺失項目
    # missing_elements 是 list[MissingElement]，每個元素包含 label 和 penalty
    # 顯示缺失項目名稱和對應的扣分，讓 HR 知道哪個問題最嚴重
    st.markdown("### 📌 缺失的重要資訊")
    if missing_list:
        for item in missing_list:
            st.markdown(f"- {item['label']}")
    else:
        st.markdown("✅ 資訊完整")
 
    st.markdown("---")
 
    # 改善建議
    st.markdown("### 💡 改善建議")
    for i, suggestion in enumerate(result["improvement_suggestions"], 1):
        # st.expander() 讓每條建議可以折疊，頁面不會太長
        with st.expander(f"建議 {i}"):
            st.markdown(suggestion)
    st.markdown("---")

    # 引導使用者進行下一步
    st.success("✅ 分析完成！請前往左側選單的「JD 改寫」繼續下一步。")