# app/routers/copilot.py
"""
模組 F：HR 知識助手 — FastAPI Router
提供單一 endpoint：POST /api/v1/copilot/query

路由策略（Rule-based dispatch，不呼叫 LLM 做意圖判斷）：
  1. 問題含「員工編號」或「工號」格式（5 位數字）→ lookup_employee
  2. 問題含假別關鍵字且含姓名或工號 → calculate_leave
  3. 其餘 → rag_search（查詢勞基法 / 公司政策知識庫）

說明：
  此路由僅負責「接收 → 分派 → 回傳」，業務邏輯全部封裝在 copilot_service.py。
  未來升級為 LangGraph Agent 時，只需替換 dispatch 邏輯，Router 介面不變。
"""

import re

import jieba.posseg as pseg
from fastapi import APIRouter, HTTPException
from langchain_openai import ChatOpenAI

from app.models.copilot_schemas import CopilotRequest, CopilotResponse
from app.services.copilot_service import (
    calculate_leave,
    lookup_employee,
    rag_search,
)

# ── LLM（用於 lookup_employee 結論合成，與 rag_search 共用同一模型）──
_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

router = APIRouter()

# ── 常用台灣姓氏（單字）─────────────────────────────────────────────
# jieba 以簡體中文訓練，部分姓氏（如「陳」）會被標為動詞 v，
# 導致後續的名字詞（nr/nz）前缺少姓氏。
# 若 nr/nz 詞的前一個 token 是常用姓氏，自動往前合併。
_COMMON_SURNAMES = set(
    "陳林黃張李王吳劉蔡楊許鄭謝洪曾邱廖賴徐周葉蘇莊呂江何蕭羅高游"
    "盧方鄧韓馮曹彭潘鍾余唐胡姜梁孫趙馬童魏石詹沈施朱翁戴鄒溫阮倪"
    "侯袁薛蔣聶范傅盛錢尤文龍杜田藍關黎史嚴夏歐柳葛陸戚邵孟"
)

# ── 關鍵字集（用於 Rule-based dispatch）─────────────────────────
_LEAVE_KEYWORDS = {"特休", "事假", "病假", "生理假", "婚假", "喪假",
                   "產假", "陪產假", "育嬰假", "補休", "公假", "假期", "餘額",
                   "請假", "假別", "假況", "假狀"}
_EMPLOYEE_KEYWORDS = {"員工", "工號", "姓名", "職稱", "部門", "薪資", "到職",
                      "基本資料", "資料", "聯絡", "信箱", "email"}

# 5 位數字員工編號（例：10001）
# 用 lookaround 取代 \b，避免 CJK 字元前後的邊界判斷不穩定
_EMP_ID_PATTERN = re.compile(r"(?<!\d)\d{5}(?!\d)")


def _extract_name(text: str) -> str | None:
    """
    從句子中萃取人名，三層策略：

    Layer 1（jieba nr/nz）：
      - 單字 nr  → 往後補緊接的純中文段落（補完名字）
      - 多字 nr/nz → 往前看是否有常用姓氏被誤標，若有則合併

    Layer 2（regex fallback）：
      jieba 若完全未標出 nr/nz，用正規表示式直接在文字中
      比對「常用姓氏 + 1–3 中文字」的模式，作為保底。

    範例：
      「許志豪的請假狀況」 → jieba 可能標為 [許/v, 志豪/n] → regex 抓 '許志豪'
      「謝佳穎的基本資料」 → jieba 可能標為 [謝/v, 佳穎/nz] → Layer 1 ② 合併
    """
    word_list = list(pseg.cut(text))

    # ── Layer 1：依 jieba 詞性抓人名 ─────────────────────────────
    for i, (word, flag) in enumerate(word_list):
        if flag in ("nr", "nz"):
            # ① 單字姓，往後補名
            if len(word) == 1 and i + 1 < len(word_list):
                next_word, next_flag = word_list[i + 1]
                if re.match(r"^[\u4e00-\u9fff]+$", next_word) \
                        and next_flag not in ("v", "d", "m", "r", "p"):
                    return word + next_word

            # ② 多字 nr/nz（可能只是「名」，「姓」被誤標為 v/n）：
            #    往前看上一個 token 是否為常用姓氏
            if len(word) >= 2 and i > 0:
                prev_word, _ = word_list[i - 1]
                if len(prev_word) == 1 and prev_word in _COMMON_SURNAMES:
                    return prev_word + word

            return word

    # ── Layer 2：regex fallback（姓氏 + 1–3 中文字）─────────────
    # 用 lookahead 定義名字邊界：名字後面必須接停用字、數字、空白或結尾。
    # 這比「事後過濾」更可靠——貪婪匹配不會把「的」吃進名字裡。
    # 例：「王大明的基本資料」→ 名字後接「的」→ 正確抓到「王大明」
    _STOP = "的了在是他她我你們都也很就這那什麼，。！？「」、"
    surnames_str = "".join(_COMMON_SURNAMES)
    pattern = re.compile(
        r"([" + surnames_str + r"])"
        r"([\u4e00-\u9fff]{1,3})"
        r"(?=[" + _STOP + r"\d\s]|$)"   # lookahead：名字後必須接停用字或結尾
    )
    for m in pattern.finditer(text):
        full_name = m.group(0)
        if len(full_name) >= 2:
            return full_name

    return None


def _dispatch(question: str) -> CopilotResponse:
    """
    依問題內容選擇最合適的 Tool 並回傳結果。
    """
    q = question.strip()

    # ── 優先：偵測到員工編號（5 位數）─────────────────────────────
    id_match = _EMP_ID_PATTERN.search(q)

    # ── 假別相關問題 ───────────────────────────────────────────────
    has_leave = any(kw in q for kw in _LEAVE_KEYWORDS)

    def _leave_response(identifier: str) -> CopilotResponse:
        """呼叫 calculate_leave，加 LLM 結論合成後回傳。"""
        raw = calculate_leave.invoke({"identifier": identifier})
        if not raw.startswith("查無員工"):
            prompt = (
                "你是一位專業 HR 助理。根據以下假別資料，用一句話直接回答使用者的問題。\n"
                "只回答問題所問的內容，不要重複完整清單。\n\n"
                f"使用者問題：{q}\n\n"
                f"假別資料：\n{raw}"
            )
            conclusion = _llm.invoke(prompt).content.strip()
            answer = f"{conclusion}\n\n---\n**📅 假別詳情**\n\n```\n{raw}\n```"
        else:
            answer = raw
        return CopilotResponse(answer=answer, tool_used="calculate_leave")

    if has_leave and id_match:
        # 有假別關鍵字 + 員工編號 → calculate_leave
        return _leave_response(id_match.group())

    if has_leave:
        # 有假別關鍵字，用 jieba 萃取人名
        # 長度須 >= 2 才視為人名（避免假別詞本身的字被誤標為 nr）
        name = _extract_name(q)
        if name and len(name) >= 2:
            return _leave_response(name)

    # ── 員工基本資料查詢 ───────────────────────────────────────────
    has_employee = any(kw in q for kw in _EMPLOYEE_KEYWORDS) or id_match
    if has_employee and not has_leave:
        if id_match:
            identifier = id_match.group()
        else:
            identifier = _extract_name(q)
        if identifier and (id_match or len(identifier) >= 2):
            raw = lookup_employee.invoke({"identifier": identifier})
            # ── 用 LLM 合成一句結論，再附完整資料卡 ────────────────
            if not raw.startswith("查無員工"):
                prompt = (
                    "你是一位專業 HR 助理。根據以下員工資料，用一句話直接回答使用者的問題。\n"
                    "只回答問題所問的內容，不要重複完整資料。\n\n"
                    f"使用者問題：{q}\n\n"
                    f"員工資料：\n{raw}"
                )
                conclusion = _llm.invoke(prompt).content.strip()
                answer = f"{conclusion}\n\n---\n**👤 員工完整資料**\n\n```\n{raw}\n```"
            else:
                answer = raw
            return CopilotResponse(answer=answer, tool_used="lookup_employee")

    # ── 其餘：查詢 HR 知識庫 ──────────────────────────────────────
    answer = rag_search.invoke({"query": q})
    return CopilotResponse(answer=answer, tool_used="rag_search")


# ════════════════════════════════════════════════════════════════
# Endpoint
# ════════════════════════════════════════════════════════════════

@router.post("/copilot/query", response_model=CopilotResponse)
def copilot_query(request: CopilotRequest) -> CopilotResponse:
    """
    HR 知識助手主入口。

    - 輸入：{"question": "使用者問題"}
    - 輸出：{"answer": "...", "tool_used": "rag_search | lookup_employee | calculate_leave | none"}
    """
    try:
        return _dispatch(request.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))