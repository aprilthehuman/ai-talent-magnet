"""
AI Talent Magnet — Streamlit 前端主入口
架構：多頁面應用，每個 Module 是獨立頁面
"""


import streamlit as st


# ── 頁面基本設定 ──────────────────────────────────────────
# 這行必須是檔案中第一個 st 指令，設定瀏覽器分頁的標題和版面
st.set_page_config(
    page_title="AI Talent Magnet",
    page_icon="🧲",
    layout="wide"          # 使用寬版版面，比預設的窄版更適合工具型介面
)

# ── Session State 初始化 ──────────────────────────────────
# session_state 就像一個字典，在使用者整個使用過程中持續存在
# 我們在這裡統一定義所有 key，方便日後各頁面共用
# 只有 key 不存在時才初始化，避免每次重新執行時把資料清掉

if "module_a_result" not in st.session_state:
    st.session_state["module_a_result"] = None   # Module A 的分析結果

if "module_b_result" not in st.session_state:
    st.session_state["module_b_result"] = None   # Module B 的改寫結果

if "module_d_result" not in st.session_state:
    st.session_state["module_d_result"] = None   # Module D 的 Persona 結果

if "module_e_result" not in st.session_state:
    st.session_state["module_e_result"] = None   # Module E 的 Sourcing 結果

if "company_profile" not in st.session_state:
    st.session_state["company_profile"] = None   # 共用的 Company Profile

if "selected_jd" not in st.session_state:
    st.session_state["selected_jd"] = None       # B 選定的改寫版本，傳給 D 用

if "original_jd" not in st.session_state:
    st.session_state["original_jd"] = ""         # 原始 JD 文字，A/B 共用

if "target_candidate_focus" not in st.session_state:
    st.session_state["target_candidate_focus"] = None   # Module B 收集的目標候選人特質，獨立存放（不在 company_profile 內）

if "education_preference" not in st.session_state:
    st.session_state["education_preference"] = None     # Module D 收集的學歷參考條件，供 Module E 使用

# Module A 收集的 job_title 與三個選填欄位，因為不在 AnalyzeJDResponse 輸出裡，需要獨立存放
if "job_title" not in st.session_state:
    st.session_state["job_title"] = ""

if "company_type" not in st.session_state:
    st.session_state["company_type"] = None

if "industry" not in st.session_state:
    st.session_state["industry"] = None

if "seniority_level" not in st.session_state:
    st.session_state["seniority_level"] = None


# ── 首頁內容 ─────────────────────────────────────────────
st.title("🧲 AI Talent Magnet")
st.subheader("以 AI 技術提升企業招募吸引力的系統")

st.markdown("---")

st.markdown("""
### 使用流程

請依照以下順序使用各功能模組：

1. **JD 吸引力分析**（左側選單）→ 分析你的 JD 有哪些問題
2. **JD 改寫**（左側選單）→ 根據公司文化產出三種改寫版本
3. **候選人 Persona**（左側選單）→ 反推理想候選人樣貌
4. **Sourcing 助手**（左側選單）→ 生成搜尋語法與主動聯繫訊息
""")

st.markdown("---")

# st.columns() 把頁面切成幾欄並排顯示
col1, col2, col3, col4 = st.columns(4)

with col1:
    status_a = "✅ 已完成" if st.session_state["module_a_result"] else "⏳ 尚未執行"
    st.metric(label="Module A：JD 分析", value=status_a)

with col2:
    status_b = "✅ 已完成" if st.session_state["module_b_result"] else "⏳ 尚未執行"
    st.metric(label="Module B：JD 改寫", value=status_b)

with col3:
    status_d = "✅ 已完成" if st.session_state["module_d_result"] else "⏳ 尚未執行"
    st.metric(label="Module D：人才 Persona", value=status_d)

with col4:
    status_e = "✅ 已完成" if st.session_state["module_e_result"] else "⏳ 尚未執行"
    st.metric(label="Module E：Sourcing 助手", value=status_e)

st.markdown("---")
st.caption("版本 v1.5.3 ‧ 作者：April")