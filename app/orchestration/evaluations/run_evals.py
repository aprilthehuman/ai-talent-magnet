"""
Module G Evaluation Runner — v1.7 更新
執行所有 eval_cases，印出測試結果摘要。

執行方式：
  python -m app.orchestration.evaluations.run_evals

輸出格式：
  PASS / FAIL，並列出失敗原因，方便快速定位問題。

v1.7 新增斷言類型：
  - should_clarify  : clarify_node 是否觸發補問
  - parsed_intent   : parse_input_node 提取的意圖
  - extracted_field : parse_input_node 提取的欄位（含 company_name_in_report、salary_extracted）
  - branch_decision : branch_node 的路由決策

v1.7 移除：
  - should_raise    : model_validator 已移除 company_profile 必填驗證（C6 重新設計）
"""

from pydantic import ValidationError

from app.models.agent_schemas import AgentRequest, AgentResponse
from app.orchestration.agent_service import run_agent
from app.orchestration.evaluations.eval_cases import EVAL_CASES


def run_single_case(case: dict) -> dict:
    """
    執行單一 eval case，回傳結果 dict：
      passed  : bool
      reason  : 失敗原因（passed=True 時為空字串）
    """
    expected = case["expected"]

    # ── 已廢棄：should_raise（v1.7 model_validator 已移除）──────────────
    # 保留向下相容性，若舊 case 有此欄位仍可執行，但 v1.7 eval_cases 不再使用
    if "should_raise" in expected:
        try:
            AgentRequest(**case["input"])
            return {"passed": False, "reason": "預期拋出例外，但沒有發生（注意：v1.7 已移除 model_validator，此 case 應更新）"}
        except (ValueError, ValidationError):
            return {"passed": True, "reason": ""}

    # ── 建立 Request 並執行 Agent ────────────────────────────────────────
    try:
        request = AgentRequest(**case["input"])
        response: AgentResponse = run_agent(request)
    except Exception as e:
        return {"passed": False, "reason": f"執行時發生例外：{e}"}

    # ── 斷言 1：should_clarify（v1.7 新增）──────────────────────────────
    # 預期 clarify_node 觸發補問：clarification_needed=True
    if "should_clarify" in expected:
        if not getattr(response, "clarification_needed", False):
            return {
                "passed": False,
                "reason": (
                    "預期 clarification_needed=True，但 Agent 直接執行了完整流程。\n"
                    f"  response.clarification_needed = {getattr(response, 'clarification_needed', 'N/A')}"
                ),
            }
        # 補問情境：report_contains 改為驗證補問訊息（clarification_message 或 final_report）
        clarification_msg = getattr(response, "clarification_message", "") or response.final_report
        for keyword in expected.get("report_contains", []):
            if keyword not in clarification_msg:
                return {
                    "passed": False,
                    "reason": (
                        f"補問訊息缺少關鍵字：「{keyword}」\n"
                        f"  實際補問訊息前 300 字：\n{clarification_msg[:300]}"
                    ),
                }
        return {"passed": True, "reason": ""}

    # ── 斷言 2：parsed_intent（v1.7 新增）───────────────────────────────
    # 驗證 parse_input_node 提取的意圖字串包含預期值
    if "parsed_intent" in expected:
        actual_intent = getattr(response, "parsed_intent", None)
        if actual_intent is None:
            return {
                "passed": False,
                "reason": "response.parsed_intent 為 None，parse_input_node 未提取意圖",
            }
        if expected["parsed_intent"] not in str(actual_intent):
            return {
                "passed": False,
                "reason": (
                    f"parsed_intent 不符\n"
                    f"  預期包含：{expected['parsed_intent']}\n"
                    f"  實際：{actual_intent}"
                ),
            }

    # ── 斷言 3：branch_decision ──────────────────────────────────────────
    # 驗證 branch_node 的路由決策
    if "branch_decision" in expected:
        actual_branch = getattr(response, "branch_decision", None)
        if actual_branch != expected["branch_decision"]:
            return {
                "passed": False,
                "reason": (
                    f"branch_decision 不符\n"
                    f"  預期：{expected['branch_decision']}\n"
                    f"  實際：{actual_branch}"
                ),
            }

    # ── 斷言 4：steps_taken ──────────────────────────────────────────────
    expected_steps = set(expected.get("steps_taken", []))
    if expected_steps:
        actual_steps = set(response.steps_taken)
        if expected_steps != actual_steps:
            return {
                "passed": False,
                "reason": (
                    f"steps_taken 不符\n"
                    f"  預期：{expected_steps}\n"
                    f"  實際：{actual_steps}"
                ),
            }

    # ── 斷言 5：extracted_field（v1.7 新增）─────────────────────────────
    # 驗證 parse_input_node 從自然語言提取的欄位
    if "extracted_field" in expected:
        for field_key, expected_value in expected["extracted_field"].items():

            # company_name_in_report：final_report 中應出現公司名稱
            if field_key == "company_name_in_report":
                if expected_value not in response.final_report:
                    return {
                        "passed": False,
                        "reason": (
                            f"final_report 中未出現公司名稱「{expected_value}」\n"
                            f"  （parse_input_node 可能未正確提取 company_name）"
                        ),
                    }

            # salary_extracted：response 中應有 salary_min/max（或 final_report 含薪資數字）
            elif field_key == "salary_extracted" and expected_value is True:
                parsed_salary = (
                    getattr(response, "salary_min", None)
                    or getattr(response, "salary_max", None)
                    or any(
                        keyword in response.final_report
                        for keyword in ["70,000", "90,000", "70K", "90K", "70k", "90k"]
                    )
                )
                if not parsed_salary:
                    return {
                        "passed": False,
                        "reason": (
                            "parse_input_node 未從 user_input 提取薪資資訊（salary_min/max 為空，"
                            "且 final_report 中無薪資數字）"
                        ),
                    }

    # ── 斷言 6：final_report 包含關鍵字 ─────────────────────────────────
    for keyword in expected.get("report_contains", []):
        if keyword not in response.final_report:
            return {
                "passed": False,
                "reason": (
                    f"final_report 缺少關鍵字：「{keyword}」\n"
                    f"  實際 final_report 前 500 字：\n{response.final_report[:500]}"
                ),
            }

    # ── 斷言 7：error_messages 為空 ──────────────────────────────────────
    if response.error_messages:
        return {
            "passed": False,
            "reason": f"error_messages 不為空：{response.error_messages}",
        }

    return {"passed": True, "reason": ""}


def main():
    print("=" * 60)
    print("Module G Evaluation Runner  (v1.7)")
    print("=" * 60)

    results = []
    for case in EVAL_CASES:
        print(f"\n[{case['id']}] {case['description']}")
        result = run_single_case(case)
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  → {status}")
        if not result["passed"]:
            print(f"     原因：{result['reason']}")
        results.append(result)

    # 摘要
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print("\n" + "=" * 60)
    print(f"結果：{passed} / {total} 通過")
    print("=" * 60)


if __name__ == "__main__":
    main()