"""
模組 A：JD Attraction Analyzer
輸入一份職缺描述（JD），系統透過規則層 + AI 層混合評分，
分析這份 JD 的吸引力並找出問題。

輸出分為兩類：
  1. 純 Python 規則層（不呼叫 LLM）：
     - negative_keywords_detected：掃描負面詞彙字典
     - vague_phrases_detected：掃描模糊用語列表
     - missing_elements：檢查五大缺失項目（薪資、成長、文化、工作內容、影響力）

  2. LLM 生成（AI 層）：
     - attraction_score：結合規則層扣分與 AI 語氣分數計算
     - score_label：根據分數對應四級等級標籤
     - tone_analysis：80-100 字的整體語氣分析
     - improvement_suggestions：三條【問題】→【原因】→【建議】結構化改善建議
"""


from pydantic import BaseModel, Field
from typing import Optional


# ── 輸入 Schema ──────────────────────────────────────────

class AnalyzeJDRequest(BaseModel):
    """
    模組 A 的輸入資料結構。
    欄位來源分兩類：
      - HR 必填：job_title、job_description_text
      - HR 選填（傳入 AI 層作為分析背景）：company_type、industry、seniority_level
    """
    job_title: str = Field(
        ...,
        description="職稱，例：Python Backend Engineer"
    )
    job_description_text: str = Field(
        ...,
        description="完整 JD 文字，建議 100–5000 字"
    )
    company_type: Optional[str] = Field(
        default=None,
        description="公司類型，例：startup / SME / enterprise。傳入 AI 層，影響語氣分析角度"
    )
    industry: Optional[str] = Field(
        default=None,
        description="產業類型，例：SaaS / 電商 / 金融。傳入 AI 層，影響語氣分析角度"
    )
    seniority_level: Optional[str] = Field(
        default=None,
        description="年資層級，例：junior / mid / senior。傳入 AI 層，影響語氣分析角度"
    )


# ── 輸出子結構 ────────────────────────────────────────────

class MissingElement(BaseModel):
    """
    單一缺失項目的資料結構。
    獨立定義成 class 讓前端可以用 item.label、item.penalty 直接存取，
    方便之後在 UI 上顯示每個缺失項目的扣分明細。
    """
    label: str = Field(..., description="缺失項目說明，例：未提供薪資範圍")
    penalty: int = Field(..., description="此項目的扣分數")


# ── 輸出 Schema ──────────────────────────────────────────

class AnalyzeJDResponse(BaseModel):
    """
    模組 A 的輸出資料結構。
    前端可直接用各欄位渲染對應的 UI 區塊：
      - attraction_score + score_label → 分數儀表板與等級標籤
      - tone_analysis → 語氣分析段落
      - negative_keywords_detected → 負面詞彙高亮區
      - vague_phrases_detected → 模糊用語高亮區
      - missing_elements → 缺失項目清單（含扣分明細）
      - improvement_suggestions → 改善建議列表
    """
    attraction_score: int = Field(
        ...,
        description="綜合吸引力分數（0–100）"
    )
    score_label: str = Field(
        ...,
        description="分數等級標籤：優良（80-100）/ 普通（60-79）/ 偏低（40-59）/ 危險（0-39）"
    )
    tone_analysis: str = Field(
        ...,
        description="80-100 字的整體語氣分析，涵蓋語氣風格、吸引力程度、整體感受"
    )
    negative_keywords_detected: list[str] = Field(
        ...,
        description="偵測到的負面詞彙清單，每個詞扣 5 分"
    )
    vague_phrases_detected: list[str] = Field(
        ...,
        description="偵測到的模糊用語清單，每個詞扣 3 分"
    )
    missing_elements: list[MissingElement] = Field(
        ...,
        description="缺失的重要資訊清單，含每項的扣分數"
    )
    improvement_suggestions: list[str] = Field(
        ...,
        description="三條改善建議，格式為【問題】→【原因】→【建議】，每條 40-60 字"
    )