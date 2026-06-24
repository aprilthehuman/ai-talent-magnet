"""
模組 E：AI Sourcing Assistant
輸入整合模組 A（job_title）與模組 D（persona 完整欄位 + education_preference），
HR 不需重複填寫任何資訊，只需選填 additional_keywords 與 exclude_keywords。

輸出分為兩類：
  1. 純 Python 邏輯組裝（不呼叫 LLM）：
     - expanded_titles：查職稱同義詞字典展開
     - boolean_string_*：五種平台搜尋語法

  2. LLM 生成：
     - outreach_message_template：整合 Persona 溝通偏好生成通用破冰訊息
     - sourcing_tips：針對此職缺與候選人特性給出實戰 sourcing 建議
"""


from pydantic import BaseModel, Field
from typing import Literal
from app.models.persona_schemas import EducationPreference


# ── 輸入 Schema ──────────────────────────────────────────

class SourcingRequest(BaseModel):
    """
    Module E 的輸入資料結構。
    所有欄位來源分三類：
      - 模組 A 帶入：job_title
      - 模組 D 帶入：其餘 Persona 欄位 + education_preference
      - HR 選填補充：additional_keywords、exclude_keywords
    """
    # 從模組 A 帶入
    job_title: str = Field(..., description="職稱")

    # 從模組 D 帶入
    key_skills: list[str] = Field(..., description="核心技能清單")
    ideal_seniority: str = Field(..., description="理想年資")
    likely_channels: list[str] = Field(..., description="候選人常出現的平台")
    likely_background: list[str] = Field(..., description="LLM 推斷的候選人背景描述")
    candidate_motivators: list[str] = Field(..., description="候選人在意的面向")
    likely_concerns: list[str] = Field(..., description="候選人常見顧慮")
    preferred_message_style: str = Field(..., description="溝通偏好")
    education_preference: EducationPreference | None = Field(
        default=None,
        description="HR 填寫的學歷參考條件，用於 sourcing tips"
    )

    # HR 選填補充
    additional_keywords: list[str] = Field(
        default_factory=list,
        description="HR 額外補充的關鍵字"
    )
    exclude_keywords: list[str] = Field(
        default_factory=list,
        description="想排除的詞彙"
    )


# ── 輸出 Schema ──────────────────────────────────────────

class SourcingResult(BaseModel):
    """
    Module E 的輸出資料結構。
    Boolean string 分三個平台區塊，每個區塊含內建搜尋語法和 Google X-Ray 語法：

    區塊一 LinkedIn：
      - boolean_string_linkedin：LinkedIn 內建搜尋語法（需帳號）
      - boolean_string_google_linkedin：Google X-Ray 搜尋 LinkedIn（免費）

    區塊二 CakeResume：
      - boolean_string_cake：CakeResume 內建搜尋語法（需帳號）
      - boolean_string_google_cake：Google X-Ray 搜尋 CakeResume（免費）

    區塊三 104：
      - boolean_string_google_104：Google X-Ray 搜尋 104（主動搜尋履歷需企業帳號）
    """
    expanded_titles: list[str] = Field(..., description="職稱同義展開結果")

    # 區塊一：LinkedIn
    boolean_string_linkedin: str = Field(..., description="LinkedIn 內建搜尋語法")
    boolean_string_google_linkedin: str = Field(..., description="Google X-Ray 搜尋 LinkedIn")

    # 區塊二：CakeResume
    boolean_string_cake: str = Field(..., description="CakeResume 內建搜尋語法")
    boolean_string_google_cake: str = Field(..., description="Google X-Ray 搜尋 CakeResume")

    # 區塊三：104
    boolean_string_google_104: str = Field(..., description="Google X-Ray 搜尋 104")

    outreach_message_template: str = Field(..., description="通用破冰聯繫訊息範本")
    sourcing_tips: list[str] = Field(..., description="sourcing 建議")