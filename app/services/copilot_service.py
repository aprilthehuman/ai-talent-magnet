# app/services/copilot_service.py
"""
Module F：HR 知識助手 — LangChain Tools 定義
包含 3 個 Tool，供後續 LangGraph Agent 呼叫：
  - rag_search      : 查詢 ChromaDB，回答勞基法與公司政策問題
  - lookup_employee : 查詢 employees.csv，取得員工基本資料
  - calculate_leave : 查詢 leave_records.csv，計算特休餘額
"""

# 1. 標準函式庫
import sys
from pathlib import Path
from datetime import date

# 2. 將專案根目錄加入 sys.path（必須在本地模組 import 之前）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# 3. 第三方套件
import pandas as pd
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

# 4. 本地模組
from app.config import (
    DATA_DIR,
    VECTOR_STORE_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
)

# 5. 執行邏輯
load_dotenv()

# ── ChromaDB 初始化（模組載入時執行一次，避免重複開啟）────────────
_embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_vectorstore = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=_embeddings,
    persist_directory=str(VECTOR_STORE_DIR),
)
# 相關性門檻：低於此分數的文件視為「無關」，不顯示在參考資料區塊
_RAG_RELEVANCE_THRESHOLD = 0.5

# ── CSV 路徑 ──────────────────────────────────────────────────────
_EMPLOYEES_CSV     = DATA_DIR / "employees.csv"
_LEAVE_RECORDS_CSV = DATA_DIR / "leave_records.csv"


# ── 特休天數計算（依勞基法第 38 條）──────────────────────────────
def _entitled_leave_days(hire_date: date, reference_date: date) -> int:
    """依年資計算本年度特休應給天數。"""
    years = (reference_date - hire_date).days / 365.25

    if years < 0.5:
        return 0
    elif years < 1:
        return 3
    elif years < 2:
        return 7
    elif years < 3:
        return 10
    elif years < 5:
        return 14
    elif years < 10:
        return 15
    else:
        extra = int(years) - 10
        return min(16 + extra, 30)


# ════════════════════════════════════════════════════════════════
# Tool 1：RAG 查詢（勞基法 / 公司政策）
# ════════════════════════════════════════════════════════════════
@tool
def rag_search(query: str) -> str:
    """
    查詢 HR 知識庫，回答勞動法規與公司政策相關問題。
    適用情境：試用期、特休規定、資遣費、請假流程、招募政策等。

    Args:
        query: 使用者的問題，例如「試用期最長幾個月？」

    Returns:
        相關知識庫段落，格式為「來源 + 內容」的清單。
    """
    scored_docs = _vectorstore.similarity_search_with_relevance_scores(query, k=3)

    if not scored_docs:
        return "知識庫中未找到相關資料，請洽 HR 部門確認。"

    relevant_docs = [(doc, score) for doc, score in scored_docs
                     if score >= _RAG_RELEVANCE_THRESHOLD]

    context_for_llm = []
    for i, (doc, score) in enumerate(scored_docs, start=1):
        content = doc.page_content.strip()
        context_for_llm.append(f"[{i}] {content}")

    context_text = "\n\n".join(context_for_llm)
    prompt = (
        "你是一位專業且親切的 HR 助理，請根據以下知識庫段落回答使用者問題。\n"
        "有相關資訊時：給出簡潔結論（2–4 句），不要列點，不要重複來源編號。\n"
        "無相關資訊時：不要捏造答案，但仍要以親切的語氣說明知識庫中沒有此資訊，"
        "並視情況給予實用建議（如：建議查詢哪裡、聯絡誰等）。\n\n"
        f"使用者問題：{query}\n\n"
        f"知識庫段落：\n{context_text}"
    )
    conclusion = _llm.invoke(prompt).content.strip()

    if not relevant_docs:
        return conclusion

    ref_blocks = []
    for i, (doc, score) in enumerate(relevant_docs, start=1):
        source  = doc.metadata.get("file", "未知來源")
        section = doc.metadata.get("h2", "")
        content = doc.page_content.strip()
        ref_blocks.append(f"[{i}] 來源：{source}｜{section}\n{content}")

    ref_cards = []
    for block in ref_blocks:
        quoted = "\n".join(f"> {line}" if line else ">" for line in block.splitlines())
        ref_cards.append(quoted)
    refs_text = "\n\n".join(ref_cards)
    return f"{conclusion}\n\n---\n**📎 參考資料**\n\n{refs_text}"


# ════════════════════════════════════════════════════════════════
# Tool 2：員工資料查詢
# ════════════════════════════════════════════════════════════════
@tool
def lookup_employee(identifier: str) -> str:
    """
    依員工姓名或員工編號查詢基本資料。

    Args:
        identifier: 員工姓名（如「王大明」）或員工編號（如「10001」）

    Returns:
        員工基本資料，包含部門、職稱、到職日、薪資等。
    """
    df = pd.read_csv(_EMPLOYEES_CSV, dtype={"employee_id": str})

    mask = (df["employee_id"] == identifier) | (df["name"] == identifier)
    result = df[mask]

    if result.empty:
        return f"查無員工資料：「{identifier}」，請確認姓名或員工編號是否正確。"

    row = result.iloc[0]
    return (
        f"員工編號：{row['employee_id']}\n"
        f"姓　　名：{row['name']}\n"
        f"部　　門：{row['department']}\n"
        f"職　　稱：{row['position']}\n"
        f"到職日期：{row['hire_date']}\n"
        f"在職狀態：{row['status']}\n"
        f"月薪（元）：{int(row['monthly_salary']):,}\n"
        f"電子信箱：{row['email']}"
    )


# ════════════════════════════════════════════════════════════════
# Tool 3：假別餘額計算
# ════════════════════════════════════════════════════════════════

_ANNUAL_LEAVE_QUOTA = {
    "特休": None,   # 動態計算，見 _entitled_leave_days()
    "事假": 14,
    "病假": 30,
    "生理假": 3,
}

_EVENT_LEAVE_TYPES = ["婚假", "喪假", "產假", "陪產假", "育嬰假", "補休", "公假"]


@tool
def calculate_leave(identifier: str) -> str:
    """
    計算員工本年度各假別使用情況與剩餘天數。

    Args:
        identifier: 員工姓名（如「王大明」）或員工編號（如「10001」）

    Returns:
        各假別使用情況的完整清單。
    """
    emp_df   = pd.read_csv(_EMPLOYEES_CSV, dtype={"employee_id": str})
    leave_df = pd.read_csv(_LEAVE_RECORDS_CSV, dtype={"employee_id": str})

    mask   = (emp_df["employee_id"] == identifier) | (emp_df["name"] == identifier)
    result = emp_df[mask]

    if result.empty:
        return f"查無員工資料：「{identifier}」，請確認姓名或員工編號是否正確。"

    row          = result.iloc[0]
    employee_id  = str(row["employee_id"])
    name         = row["name"]
    hire_date    = date.fromisoformat(row["hire_date"])
    today        = date.today()
    current_year = today.year
    years_of_service = (today - hire_date).days / 365.25

    approved_df = leave_df[
        (leave_df["employee_id"] == employee_id) &
        (leave_df["status"] == "approved") &
        (leave_df["year"] == current_year)
    ]
    used_by_type = approved_df.groupby("leave_type")["days"].sum().to_dict()

    lines = [
        f"員工：{name}（{employee_id}）",
        f"到職日：{hire_date}｜年資：{years_of_service:.1f} 年",
        f"統計年度：{current_year} 年",
        "",
        "【年度額度假別】",
    ]

    gender = str(row.get("gender", "M")).strip().upper()

    for leave_type, quota in _ANNUAL_LEAVE_QUOTA.items():
        if leave_type == "生理假" and gender != "F":
            continue
        entitled  = _entitled_leave_days(hire_date, today) if quota is None else quota
        used      = int(used_by_type.get(leave_type, 0))
        remaining = entitled - used
        lines.append(f"  {leave_type}")
        lines.append(f"    應給 {entitled} 天 / 已使用 {used} 天 / 剩餘 {remaining} 天")

    lines.append("")
    lines.append("【事件型假別（本年度已使用）】")

    event_used = False
    for leave_type in _EVENT_LEAVE_TYPES:
        used = int(used_by_type.get(leave_type, 0))
        if used > 0:
            lines.append(f"  {leave_type}：{used} 天")
            event_used = True

    if not event_used:
        lines.append("  本年度無紀錄")

    return "\n".join(lines)