"""
Module G Evaluation Runner
執行所有 eval_cases，印出測試結果摘要。

執行方式：
  python -m app.orchestration.evaluations.run_evals

輸出格式：
  PASS / FAIL，並列出失敗原因，方便快速定位問題。
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
    case_id = case["id"]
    expected = case["expected"]

    # Case 6 這類預期拋出例外的情境
    if "should_raise" in expected:
        try:
            AgentRequest(**case["input"])
            return {"passed": False, "reason": "預期拋出例外，但沒有發生"}
        except (ValueError, ValidationError):
            return {"passed": True, "reason": ""}

    # 一般情境：執行 Agent
    try:
        request = AgentRequest(**case["input"])
        response: AgentResponse = run_agent(request)
    except Exception as e:
        return {"passed": False, "reason": f"執行時發生例外：{e}"}

    # 驗證 steps_taken
    expected_steps = set(expected.get("steps_taken", []))
    actual_steps = set(response.steps_taken)
    if expected_steps != actual_steps:
        return {
            "passed": False,
            "reason": f"steps_taken 不符\n  預期：{expected_steps}\n  實際：{actual_steps}",
        }

    # 驗證 final_report 包含關鍵字
    for keyword in expected.get("report_contains", []):
        if keyword not in response.final_report:
            return {
                "passed": False,
                "reason": (
                    f"final_report 缺少關鍵字：「{keyword}」\n"
                    f"實際 final_report 前 500 字：\n{response.final_report[:500]}"
                )
            }

    # 驗證 error_messages 為空
    if response.error_messages:
        return {
            "passed": False,
            "reason": f"error_messages 不為空：{response.error_messages}",
        }

    return {"passed": True, "reason": ""}


def main():
    print("=" * 60)
    print("Module G Evaluation Runner")
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