"""
模組 F：HR 知識助手
定義 POST /api/v1/copilot/query 的輸入與輸出資料結構。

設計說明：
  - CopilotRequest  : 使用者的自然語言問題
  - CopilotResponse : AI 回答 + 呼叫了哪個 Tool（方便前端 debug）
"""

from typing import Literal
from pydantic import BaseModel, Field


# ── 輸入 Schema ──────────────────────────────────────────

class CopilotRequest(BaseModel):
    """
    HR 知識助手的輸入資料結構。
    """
    question: str = Field(
        ...,
        min_length=2,
        description="使用者的問題，例：「王大明還有幾天特休？」或「試用期最長幾個月？」",
    )


# ── 輸出 Schema ──────────────────────────────────────────

class CopilotResponse(BaseModel):
    """
    HR 知識助手的輸出資料結構。

    欄位說明：
      - answer      : AI 回答內容（純文字）
      - tool_used   : 實際呼叫的 Tool 名稱，方便前端顯示資料來源標籤
                      rag_search / lookup_employee / calculate_leave / none
    """
    answer: str = Field(
        ...,
        description="HR 知識助手的回答",
    )
    tool_used: Literal["rag_search", "lookup_employee", "calculate_leave", "none"] = Field(
        ...,
        description="本次查詢呼叫的 Tool 名稱",
    )