from pydantic import BaseModel, Field
from app.models.persona_schemas import EducationPreference


"""
模組 E：AI Sourcing Assistant
輸入整合模組 A（job_title）與模組 D（persona 完整欄位 + education_preference），
HR 不需重複填寫任何資訊，只需選填 additional_keywords 與 exclude_keywords。

輸出分為兩類：
  1. 純 Python 邏輯組裝（不呼叫 LLM）：
     - expanded_titles：查職稱同義詞字典展開
     - boolean_string_linkedin / cake / google：三段式 Boolean 字串拼接

  2. LLM 生成：
     - platform_recommendations：根據 seniority、likely_channels、education_preference 推薦平台
     - outreach_message_template：整合 Persona 溝通偏好與顧慮生成個人化訊息
     - sourcing_tips：針對此職缺與候選人特性給出實戰 sourcing 建議
"""


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
        description="HR 填寫的學歷參考條件，用於平台推薦與 sourcing tips"
    )

    # HR 選填補充
    additional_keywords: list[str] = Field(default=[], description="HR 額外補充的關鍵字")
    exclude_keywords: list[str] = Field(default=[], description="想排除的詞彙")


# ── 輸出子結構 ────────────────────────────────────────────

class PlatformRecommendation(BaseModel):
    """
    單一平台推薦的資料結構。
    platform_recommendations 是一個由多個 PlatformRecommendation 組成的 list，
    獨立定義成 class 讓前端可以用 item.platform、item.reason 直接存取，
    不需要自己解析字串。
    """
    platform: str = Field(..., description="平台名稱")
    suitability: str = Field(..., description="適用程度：高 / 中 / 低")
    reason: str = Field(..., description="推薦理由")
    search_url_hint: str | None = Field(default=None, description="搜尋入口提示")


# ── 輸出 Schema ──────────────────────────────────────────

class SourcingResult(BaseModel):
    """
    Module E 的輸出資料結構。
    前端可直接用各欄位渲染對應的 UI 區塊：
      - expanded_titles → 職稱標籤列表
      - boolean_string_* → 各平台搜尋語法區塊（含一鍵複製）
      - platform_recommendations → 平台推薦卡片
      - outreach_message_template → 可編輯的訊息草稿區
      - sourcing_tips → 建議提示列表
    """
    expanded_titles: list[str] = Field(..., description="職稱同義展開結果")
    boolean_string_linkedin: str = Field(..., description="LinkedIn Boolean string")
    boolean_string_cake: str = Field(..., description="CakeResume 搜尋語法")
    boolean_string_google: str = Field(..., description="Google X-Ray 語法")
    platform_recommendations: list[PlatformRecommendation] = Field(..., description="平台推薦清單")
    outreach_message_template: str = Field(..., description="主動聯繫訊息範本")
    sourcing_tips: list[str] = Field(..., description="sourcing 建議")