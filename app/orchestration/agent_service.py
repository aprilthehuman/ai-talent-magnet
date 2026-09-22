"""
模組 G：AI Orchestration Agent
orchestration/agent_service.py — LangGraph StateGraph 組裝與執行

職責：
  - 定義所有 Node 與 Edge，組裝成 StateGraph
  - 入口條件分支：有 jd_text 走 JD 分析路徑，無則走 Module F（HR 知識問答）
  - A→B→D 為固定管線，D 完成後由 branch_node 判斷後續
  - branch_node 條件分支：
      none     → 直接 synthesize（只需要 JD 分析與 Persona）
      salary   → 只跑 Module C → synthesize
      sourcing → 只跑 Module E → synthesize
      both     → Module C → Module E → synthesize（串行）
  - 提供 run_agent() 函式供 router 呼叫
  - 回傳 AgentResponse schema

workflow 路徑：
  有 jd_text → analyze → rewrite → persona → branch →
      none     → synthesize
      salary   → salary → synthesize
      sourcing → sourcing → synthesize
      both     → salary → sourcing → synthesize
  無 jd_text → copilot → synthesize
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


# ── synthesize_node：整合所有模組輸出，生成最終報告 ──────────

def synthesize_node(state: AgentState) -> dict:
    """
    整合所有已執行模組的輸出，呼叫 LLM 生成 Markdown 格式最終報告。
    只將「State 中存在的結果」傳給 LLM，避免 None 干擾。
    未執行的模組不會出現在報告中。
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # 收集有值的模組結果
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

    prompt = f"""你是一位專業的 HR 顧問 AI，請根據以下各模組分析結果，
整合成一份結構清晰、易於閱讀的 Markdown 報告。
報告需涵蓋所有提供的模組結果，並在最後給出綜合建議。

各模組結果：
{json.dumps(results, ensure_ascii=False, indent=2)}

使用者原始問題：{state.get("user_input", "")}
"""

    response = llm.invoke([{"role": "user", "content": prompt}])
    return {"final_report": response.content}


# ── branch_node：LLM 判斷 persona 完成後走哪條分支 ──────────

def branch_node(state: AgentState) -> dict:
    """
    用關鍵字比對決定後續分支，取代 LLM 判斷。
    優點：確定性高、不受模型隨機性影響、不花 API 費用。
    """
    user_input = state.get("user_input", "")

    # 薪資相關關鍵字
    salary_keywords  = ["薪資", "薪水", "待遇", "薪酬", "薪資競爭力", "salary"]
    # Sourcing 相關關鍵字
    sourcing_keywords = ["sourcing", "Sourcing", "找人", "搜尋管道", "招募渠道", "人才管道", "招募管道"]

    has_salary   = any(kw in user_input for kw in salary_keywords)
    has_sourcing = any(kw in user_input for kw in sourcing_keywords)

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

def route_after_jd_check(state: AgentState) -> str:
    """
    入口判斷：有 jd_text 走 JD 分析路徑（Module A→B→D），
    無 jd_text 走 HR 知識問答路徑（Module F）。
    """
    if state.get("jd_text"):
        return "analyze_node"
    return "copilot_node"


def route_after_branch(state: AgentState) -> str:
    """
    根據 branch_decision 決定 D 完成後的下一個 Node：
      none     → synthesize_node（不跑 C / E）
      salary   → salary_node（只跑 C）
      sourcing → sourcing_node（只跑 E）
      both     → salary_node（先跑 C，C 完成後串行到 E）
    """
    decision = state.get("branch_decision", "both")
    if decision == "none":
        return "synthesize_node"
    if decision == "salary":
        return "salary_node"
    if decision == "sourcing":
        return "sourcing_node"
    # both：先走 salary，salary → sourcing 由固定 edge 處理
    return "salary_node"


# ── 組裝 StateGraph ──────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # 註冊所有 Node
    graph.add_node("analyze_node", run_analyze_jd)
    graph.add_node("rewrite_node", run_rewrite_jd)
    graph.add_node("persona_node", run_generate_persona)
    graph.add_node("branch_node", branch_node)
    graph.add_node("salary_node", run_check_salary)
    graph.add_node("sourcing_node", run_generate_sourcing)
    graph.add_node("copilot_node", run_copilot_query)
    graph.add_node("synthesize_node", synthesize_node)

    # 入口條件分支：有無 jd_text
    graph.set_conditional_entry_point(
        route_after_jd_check,
        {
            "analyze_node": "analyze_node",
            "copilot_node": "copilot_node",
        },
    )

    # JD 分析固定管線：A → B → D → branch
    graph.add_edge("analyze_node", "rewrite_node")
    graph.add_edge("rewrite_node", "persona_node")
    graph.add_edge("persona_node", "branch_node")

    # branch 後的條件分支
    graph.add_conditional_edges(
        "branch_node",
        route_after_branch,
        {
            "synthesize_node": "synthesize_node",   # none
            "salary_node": "salary_node",            # salary / both
            "sourcing_node": "sourcing_node",        # sourcing
        },
    )

    # both 路徑：C 完成後串行到 E
    # salary_only 路徑：C 完成後直接到 synthesize
    # 兩者共用 salary_node，靠 route_after_salary 區分
    graph.add_conditional_edges(
        "salary_node",
        lambda s: "sourcing_node" if s.get("branch_decision") == "both" else "synthesize_node",
        {
            "sourcing_node": "sourcing_node",
            "synthesize_node": "synthesize_node",
        },
    )

    # E 完成後一律到 synthesize
    graph.add_edge("sourcing_node", "synthesize_node")

    # Module F 路徑：copilot 完成後直接 synthesize
    graph.add_edge("copilot_node", "synthesize_node")

    # 結束
    graph.add_edge("synthesize_node", END)

    return graph.compile()


# ── 對外介面：run_agent() ────────────────────────────────────

# module 載入時編譯一次，避免每次請求重新建立 graph
_graph = build_graph()


def run_agent(request: AgentRequest) -> AgentResponse:
    """
    Agent 執行入口，供 app/routers/agent.py 呼叫。
    將 AgentRequest 轉為 initial_state，執行 LangGraph graph，
    回傳整合後的 AgentResponse。
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

    # 收集本次實際執行了哪些模組
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

    return AgentResponse(
        final_report=final_state.get("final_report", ""),
        steps_taken=steps_taken,
        error_messages=final_state.get("error_messages", []),
    )