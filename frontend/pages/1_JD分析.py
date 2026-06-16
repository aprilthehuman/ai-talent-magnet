import streamlit as st
import requests   # 用來呼叫我們的 FastAPI 後端


"""
Module A：JD Attraction Analyzer
讓使用者輸入 JD，呼叫後端 API，顯示分析結果
"""


# ── 頁面標題 ──────────────────────────────────────────────
st.title("📋 JD 吸引力分析")
st.markdown("貼上你的職缺描述，AI 幫你找出會讓候選人卻步的問題。")
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
                    "http://localhost:8000/api/v1/analyze-jd",
                    json={
                        "job_title": job_title,
                        "job_description_text": job_description,
                        "company_type": company_type if company_type else None,
                        "industry": industry if industry else None,
                        "seniority_level": seniority if seniority else None,
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
                    # st.success() 顯示綠色成功訊息
                    st.success("分析完成！")
                    
                    
                else:
                    st.error(f"API 錯誤：{response.status_code}")

            except requests.exceptions.ConnectionError:
                # 後端沒有啟動時會出現這個錯誤
                st.error("無法連接後端，請確認 FastAPI 伺服器已啟動（uvicorn app.main:app --reload）")


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

    # 語氣分析
    st.markdown("### 🎯 語氣分析")
    # st.info() 顯示藍色資訊框，適合放重要說明文字
    st.info(result["tone_analysis"])

    # 負面詞彙和模糊用語並排
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ⚠️ 偵測到的負面詞彙")
        if result["negative_keywords_detected"]:
            for kw in result["negative_keywords_detected"]:
                # st.markdown() 搭配 emoji 做成簡單的清單
                st.markdown(f"- 🔴 {kw}")
        else:
            st.markdown("✅ 無負面詞彙")

    with col2:
        st.markdown("### 💬 模糊用語")
        if result["vague_phrases_detected"]:
            for phrase in result["vague_phrases_detected"]:
                st.markdown(f"- 🟡 {phrase}")
        else:
            st.markdown("✅ 無模糊用語")

    st.markdown("---")

    # 缺失項目
    # missing_elements 現在是 list[MissingElement]，每個元素包含 label 和 penalty
    # 顯示缺失項目名稱和對應的扣分，讓 HR 知道哪個問題最嚴重
    st.markdown("### 📌 缺失的重要資訊")
    if result["missing_elements"]:
        for item in result["missing_elements"]:
            # item 是字典，用 item["label"] 取名稱，item["penalty"] 取扣分
            st.markdown(f"- {item['label']}：扣 {item['penalty']} 分")
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