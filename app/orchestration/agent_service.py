"""
模組 G：AI Orchestration Agent
orchestration/agent_service.py — LangGraph StateGraph 組裝與執行

v1.7 架構演進：
  - 新增 parse_input_node：LLM 從自然語言 Prompt 自動抽取 JD、公司資料、薪資、意圖
  - 新增 clarify_node：資訊缺失時 Agent 主動回問，不再靜默走錯路徑
  - branch_node 改用 parsed_intent（LLM 語意判斷）取代關鍵字硬比對
  - 前端表單欄位大幅簡化，使用者只需在 Prompt 中描述需求
  - company_profile 全面改為選填，不填仍可執行（以通用風格改寫）

workflow 路徑（v1.7）：
  START
    → parse_input_node（抽取結構化資料與意圖）
    → clarify_node（資訊缺失？）
        ↓ 有缺失                ↓ 資訊完整
      END（回傳提問）       route_after_jd_check
                               ↓ 有 JD            ↓ 無 JD
                           analyze_node         copilot_node
                           rewrite_node              ↓
                           persona_node         synthesize_node
                           branch_node               ↓
                     none / salary / sourcing / both  END
                               ↓
                           synthesize_node
                               ↓
                             END
"""

from __future__ import annotations

import json
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.models.agent_schemas import AgentRequest, AgentResponse
from app.orchestration.agent_state import AgentState
from app.orchestration.tools import (
    run_analyze_jd,
    run_check_salary,
    run_copilot_query,
    run_generate_persona,
    run_generate_sourcing,
    run_rewrite_jd,
)


# ── parse_input_node：自然語言 → 結構化資料 ──────────────────

def parse_input_node(state: AgentState) -> dict:
    """
    v1.7 新增：從 user_input 中用 LLM 抽取招募所需的結構化資料。

    抽取項目：
      - jd_text       ：JD 完整文字（使用者貼上的內容）
      - job_title     ：職稱
      - company_name  ：公司名稱
      - vision        ：公司願景
      - culture_keywords ：文化關鍵字清單
      - industry_context ：產業背景
      - manager_style ：管理風格
      - tone_preference ：語氣偏好
      - salary_min    ：薪資下限（數字，月薪 NT$）
      - salary_max    ：薪資上限（數字，月薪 NT$）
      - company_type  ：公司類型（新創 / 中小企業 / 大型企業 / 外商）
      - seniority_level ：職級（Junior / Mid / Senior / Lead / Manager）
      - intent        ：使用者意圖清單，可多選：
                        "rewrite"  → 改寫 JD
                        "salary"   → 薪資競爭力分析
                        "sourcing" → Sourcing 管道建議
                        "hr_qa"    → HR 知識問答（無 JD）

    若使用者未提及某欄位，填入 null（不猜測）。
    抽取失敗時，保留原始 user_input，讓後續 clarify_node 處理。
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # 若前端仍傳入了結構化欄位（向下相容），優先使用前端傳入值
    existing_jd = state.get("jd_text")
    existing_profile = state.get("company_profile") or {}

    prompt = f"""你是一位 HR AI 助理的前處理模組。
請從以下使用者輸入中，精確抽取招募相關的結構化資訊。

規則：
1. 只抽取使用者明確提到的資訊，不要推測或補充使用者未說的內容。
2. JD 文字（jd_text）：若使用者貼上了完整職缺描述，完整保留；若只是描述需求，填 null。
3. intent 必填，根據使用者想做什麼決定（可多選）：
   - "rewrite"  → 使用者想改寫 JD
   - "salary"   → 使用者想分析薪資競爭力或詢問薪資範圍
   - "sourcing" → 使用者想知道從哪裡找人才
   - "hr_qa"    → 使用者在問 HR 法規或知識（無 JD 的純問答）
4. 數字欄位（salary_min、salary_max）只填阿拉伯數字，單位統一為月薪 NT$。
   例：「月薪 6-8 萬」→ salary_min: 60000, salary_max: 80000

使用者輸入：
{state["user_input"]}

請以合法 JSON 格式回傳（不要加 markdown code block）：
{{
  "jd_text": "完整JD文字或null",
  "job_title": "職稱或null",
  "company_name": "公司名稱或null",
  "vision": "公司願景或null",
  "culture_keywords": ["關鍵字1", "關鍵字2"],
  "industry_context": "產業背景或null",
  "manager_style": "管理風格或null",
  "tone_preference": "語氣偏好或null",
  "salary_min": 數字或null,
  "salary_max": 數字或null,
  "company_type": "新創/中小企業/大型企業/外商 或null",
  "seniority_level": "Junior/Mid/Senior/Lead/Manager 或null",
  "intent": ["rewrite", "salary", "sourcing", "hr_qa 的子集"]
}}
"""

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])

        # ── Bug 修正 1：剝除 LLM 可能自動加上的 markdown code block ──
        import re
        content = response.content.strip()
        if "```" in content:
            content = re.sub(r"```(?:json)?\s*", "", content).strip()

        parsed = json.loads(content)

        # ── Bug 修正 2：intent 中英文別名對映 ────────────────────────
        intent_alias = {
            "rewrite": "rewrite", "改寫": "rewrite", "JD改寫": "rewrite",
            "salary": "salary",   "薪資": "salary",  "薪資分析": "salary",
            "sourcing": "sourcing", "找人": "sourcing", "招募管道": "sourcing",
            "hr_qa": "hr_qa", "知識問答": "hr_qa", "HR問答": "hr_qa",
        }
        valid_intents = {"rewrite", "salary", "sourcing", "hr_qa"}
        raw_intent = parsed.get("intent") or []
        parsed["intent"] = [
            intent_alias.get(i, i) for i in raw_intent
            if intent_alias.get(i, i) in valid_intents
        ]

    except (json.JSONDecodeError, Exception):
        # 解析失敗：保留原始輸入，讓 clarify_node 要求使用者補充
        return {"parsed_intent": []}

    # 組裝 company_profile（優先使用前端傳入的值，其次用 LLM 抽取的值）
    company_name  = existing_profile.get("company_name") or parsed.get("company_name")
    culture_kw    = existing_profile.get("culture_keywords") or parsed.get("culture_keywords") or []
    vision        = existing_profile.get("vision") or parsed.get("vision")
    industry      = existing_profile.get("industry_context") or parsed.get("industry_context")
    manager_style = existing_profile.get("manager_style") or parsed.get("manager_style")
    tone_pref     = existing_profile.get("tone_preference") or parsed.get("tone_preference")
    company_type  = existing_profile.get("company_type") or parsed.get("company_type")
    seniority     = existing_profile.get("seniority_level") or parsed.get("seniority_level")
    salary_min    = existing_profile.get("salary_min") or parsed.get("salary_min")
    salary_max    = existing_profile.get("salary_max") or parsed.get("salary_max")

    # ── 修正：company_profile 改為選填，任一欄位有值就組裝（原本只有 company_name 才組）──
    has_profile = any([company_name, vision, culture_kw, industry,
                       manager_style, tone_pref, company_type, seniority,
                       salary_min, salary_max])
    company_profile = {
        "company_name": company_name,
        "vision": vision,
        "culture_keywords": culture_kw,
        "industry_context": industry,
        "manager_style": manager_style,
        "tone_preference": tone_pref,
        "company_type": company_type,
        "seniority_level": seniority,
        "salary_min": salary_min,
        "salary_max": salary_max,
    } if has_profile else None

    return {
        "jd_text": existing_jd or parsed.get("jd_text"),
        "job_title": state.get("job_title") or parsed.get("job_title"),
        "company_profile": company_profile,
        "parsed_intent": parsed.get("intent") or [],
    }


# ── clarify_node：資訊缺失時主動回問 ─────────────────────────

def clarify_node(state: AgentState) -> dict:
    """
    v1.7 新增：檢查執行所需資訊是否齊全。
    資訊缺失時，回傳提問文字（clarification_needed），
    workflow 讀到非空值後終止，將提問回傳給使用者。

    缺失判斷邏輯（v1.7）：
      - intent 為空 → 請使用者說清楚需求
      - intent 包含 rewrite / salary / sourcing 但沒有 jd_text → 需要 JD
      - 注意：company_profile 已改為選填，不填仍可執行（以通用風格改寫），不再補問
    """
    intent = state.get("parsed_intent") or []
    jd_text = state.get("jd_text")

    missing_parts = []

    # 意圖完全無法判斷
    if not intent:
        return {
            "clarification_needed": (
                "我還不太確定您想要什麼 😊\n\n"
                "您可以告訴我以下任一需求：\n"
                "- 「幫我改寫這份 JD」（請附上 JD 內容）\n"
                "- 「分析這個職位的薪資競爭力」\n"
                "- 「推薦 sourcing 管道」\n"
                "- 「勞基法試用期最長幾個月？」（HR 知識問答，不需要 JD）"
            )
        }

    # 需要 JD 但沒有 JD
    jd_needed_intents = {"rewrite", "salary", "sourcing"}
    if jd_needed_intents.intersection(intent) and not jd_text:
        missing_parts.append("JD 文字（請將職缺描述貼在 Prompt 中）")

    # ── 已移除：company_name 不再是必填項目 ──────────────────────────────
    # v1.7 company_profile 全面改為選填：
    # 未填公司名稱時，改寫仍可執行（以通用風格輸出），不需要主動補問。

    if missing_parts:
        items = "\n".join(f"- {p}" for p in missing_parts)
        return {
            "clarification_needed": (
                f"需要以下補充資訊才能繼續執行：\n\n{items}\n\n"
                "請補充後重新送出，謝謝！"
            )
        }

    # 資訊完整，繼續執行
    return {"clarification_needed": None}


# ── synthesize_node：整合所有模組輸出，生成最終報告 ──────────

def synthesize_node(state: AgentState) -> dict:
    """
    整合所有已執行模組的輸出，呼叫 LLM 生成 Markdown 格式最終報告。
    只將「State 中存在的結果」傳給 LLM，避免 None 干擾。
    未執行的模組不會出現在報告中。
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    results: dict[str, Any] = {}
    if state.get("analysis_result"):
        results["JD吸引力分析"] = state["analysis_result"].model_dump()
    if state.get("rewrite_result"):
        results["JD改寫"] = state["rewrite_result"].model_dump()
    if state.get("persona_result"):
        results["候選人Persona"] = state["persona_result"].model_dump()
    if state.get("salary_result"):
        results["薪資競爭力"] = state["salary_result"].model_dump()
    if state.get("sourcing_result"):
        results["Sourcing助手"] = state["sourcing_result"].model_dump()
    if state.get("copilot_result"):
        results["HR知識助手"] = state["copilot_result"].model_dump()

    salary_hint = ""
    if state.get("salary_result"):
        cp = state.get("company_profile") or {}
        s_min = cp.get("salary_min")
        s_max = cp.get("salary_max")
        if s_min or s_max:
            salary_hint = (
                f"（使用者已提供薪資範圍：NT$ {s_min or '?'} ~ NT$ {s_max or '?'}，"
                "請在報告中顯示此範圍並與市場比較，標明是否具競爭力）"
            )
        else:
            salary_hint = (
                "（使用者未提供薪資範圍，請在報告中的薪資區塊顯示「薪資範圍：未提供」，"
                "並說明競爭力評級為市場推估值，建議補充薪資範圍後重新分析以獲得更精準結果）"
            )

    cp = state.get("company_profile") or {}
    user_context_lines = []
    if cp.get("company_name"):
        user_context_lines.append(f"- 公司名稱：{cp['company_name']}")
    if cp.get("company_type"):
        user_context_lines.append(f"- 公司類型：{cp['company_type']}")
    if cp.get("seniority_level"):
        user_context_lines.append(f"- 職級：{cp['seniority_level']}")
    if cp.get("culture_keywords"):
        user_context_lines.append(f"- 文化關鍵字：{'、'.join(cp['culture_keywords'])}")
    if cp.get("salary_min") or cp.get("salary_max"):
        s_min = cp.get("salary_min", "?")
        s_max = cp.get("salary_max", "?")
        user_context_lines.append(f"- 使用者提供薪資：NT$ {s_min} ~ NT$ {s_max}")
    if state.get("job_title"):
        user_context_lines.append(f"- 職稱：{state['job_title']}")
    user_context_str = "\n".join(user_context_lines) if user_context_lines else "（未提供額外背景資料）"

    prompt = f"""你是一位專業的 HR 顧問 AI，請根據以下各模組分析結果，
整合成一份結構清晰、易於閱讀的 Markdown 報告。

請遵守以下報告規則：

【JD 改寫規則】（僅在結果中有「JD改寫」時適用）
- 必須完整呈現三個版本：Startup 風、穩定企業風、高成長挑戰型，不得省略任何一個。
- 根據公司設定檔（company_name、vision、culture_keywords），判斷哪個版本最符合公司定位。
  若未提供公司設定檔，則不標記推薦，讓使用者自行選擇。
- 在最符合的版本標題前加上「⭐ 推薦」（有公司資料時），其餘兩個版本正常顯示即可。
- 每個版本下方附上 rewrite_notes 中對應的改寫說明（一句話）。

【薪資競爭力規則】（僅在結果中有「薪資競爭力」時適用）
{salary_hint}

【JD 吸引力分析 — 缺失元素校正規則】（僅在結果中有「JD吸引力分析」時適用）
- 分析模組只看原始 JD 文字，可能將使用者在 Prompt 中已補充的資訊標為「缺失」。
- 請對照「使用者提供的背景資料」，若缺失元素已由使用者補充，直接從缺失清單移除。
- 只有 JD 文字中確實缺少、且使用者也未補充的項目，才列入缺失元素。
- 特別注意：若 JD 本身已包含詳細的工作職責條列，「未說明具體工作內容」必須移除。
- 「未提供薪資範圍」：只要使用者有提供任何薪資數字，即視為已提供，移除此項。

【綜合建議規則】
- 綜合建議必須根據「使用者提供的背景資料」給出具體、有針對性的建議。
- 若已有薪資競爭力分析區塊，綜合建議中不要重複薪資數字，直接引導使用者參考上方結果。
- 未執行的模組不需提及。
- 使用繁體中文，語氣專業但易讀。

使用者提供的背景資料（用於校正缺失元素 & 綜合建議）：
{user_context_str}

各模組結果：
{json.dumps(results, ensure_ascii=False, indent=2)}

使用者原始問題：{state.get("user_input", "")}
"""

    response = llm.invoke([{"role": "user", "content": prompt}])
    return {"final_report": response.content}


# ── branch_node：根據 parsed_intent 決定後續分支 ─────────────

def branch_node(state: AgentState) -> dict:
    """
    v1.7：改用 parse_input_node 產出的 parsed_intent 做路由判斷，
    取代原本的關鍵字硬比對。
    """
    intent = state.get("parsed_intent") or []

    has_salary   = "salary" in intent
    has_sourcing = "sourcing" in intent

    if has_salary and has_sourcing:
        decision = "both"
    elif has_salary:
        decision = "salary"
    elif has_sourcing:
        decision = "sourcing"
    else:
        decision = "none"

    return {"branch_decision": decision}


# ── conditional edge 函式 ────────────────────────────────────

def route_after_clarify(state: AgentState) -> str:
    if state.get("clarification_needed"):
        return "end_with_clarify"
    if state.get("jd_text"):
        return "analyze_node"
    return "copilot_node"


def route_after_branch(state: AgentState) -> str:
    decision = state.get("branch_decision", "none")
    if decision == "none":
        return "synthesize_node"
    if decision == "salary":
        return "salary_node"
    if decision == "sourcing":
        return "sourcing_node"
    return "salary_node"  # both：先走 salary


# ── end_with_clarify_node：將澄清問題包成 final_report 回傳 ──

def end_with_clarify_node(state: AgentState) -> dict:
    return {"final_report": state.get("clarification_needed", "")}


# ── 組裝 StateGraph ──────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("parse_input_node", parse_input_node)
    graph.add_node("clarify_node", clarify_node)
    graph.add_node("end_with_clarify_node", end_with_clarify_node)
    graph.add_node("analyze_node", run_analyze_jd)
    graph.add_node("rewrite_node", run_rewrite_jd)

    def safe_persona_node(state: AgentState) -> dict:
        if not state.get("rewrite_result"):
            return {"error_messages": ["persona_node 跳過：rewrite_result 不存在（rewrite_node 可能失敗）"]}
        return run_generate_persona(state)

    graph.add_node("persona_node", safe_persona_node)
    graph.add_node("branch_node", branch_node)
    graph.add_node("salary_node", run_check_salary)
    graph.add_node("sourcing_node", run_generate_sourcing)
    graph.add_node("copilot_node", run_copilot_query)
    graph.add_node("synthesize_node", synthesize_node)

    graph.set_entry_point("parse_input_node")
    graph.add_edge("parse_input_node", "clarify_node")

    graph.add_conditional_edges(
        "clarify_node",
        route_after_clarify,
        {
            "end_with_clarify": "end_with_clarify_node",
            "analyze_node": "analyze_node",
            "copilot_node": "copilot_node",
        },
    )

    graph.add_edge("end_with_clarify_node", END)
    graph.add_edge("analyze_node", "rewrite_node")
    graph.add_edge("rewrite_node", "persona_node")
    graph.add_edge("persona_node", "branch_node")

    graph.add_conditional_edges(
        "branch_node",
        route_after_branch,
        {
            "synthesize_node": "synthesize_node",
            "salary_node": "salary_node",
            "sourcing_node": "sourcing_node",
        },
    )

    graph.add_conditional_edges(
        "salary_node",
        lambda s: "sourcing_node" if s.get("branch_decision") == "both" else "synthesize_node",
        {
            "sourcing_node": "sourcing_node",
            "synthesize_node": "synthesize_node",
        },
    )

    graph.add_edge("sourcing_node", "synthesize_node")
    graph.add_edge("copilot_node", "synthesize_node")
    graph.add_edge("synthesize_node", END)

    return graph.compile()


# ── 對外介面：run_agent() ────────────────────────────────────

_graph = build_graph()


def run_agent(request: AgentRequest) -> AgentResponse:
    """
    Agent 執行入口，供 app/routers/agent.py 呼叫。
    v1.7：initial_state 只需帶入 user_input 與選填的前端欄位，
    jd_text / company_profile 會由 parse_input_node 從 user_input 自動抽取。
    """
    initial_state: dict[str, Any] = {
        "messages": [],
        "user_input": request.user_input,
        "job_title": request.job_title,
        "jd_text": request.jd_text,
        "company_profile": request.company_profile,
        "error_messages": [],
    }

    final_state = _graph.invoke(initial_state)

    steps_taken = []
    if final_state.get("analysis_result"):
        steps_taken.append("analyze_jd")
    if final_state.get("rewrite_result"):
        steps_taken.append("rewrite_jd")
    if final_state.get("persona_result"):
        steps_taken.append("generate_persona")
    if final_state.get("salary_result"):
        steps_taken.append("check_salary")
    if final_state.get("sourcing_result"):
        steps_taken.append("generate_sourcing")
    if final_state.get("copilot_result"):
        steps_taken.append("copilot_query")
    if final_state.get("clarification_needed"):
        steps_taken.append("clarify")

    return AgentResponse(
        final_report=final_state.get("final_report", ""),
        steps_taken=steps_taken,
        error_messages=final_state.get("error_messages", []),
        # ── v1.7 新增：eval 斷言所需欄位 ──
        clarification_needed=final_state.get("clarification_needed"),
        parsed_intent=final_state.get("parsed_intent") or [],
        branch_decision=final_state.get("branch_decision"),
    )