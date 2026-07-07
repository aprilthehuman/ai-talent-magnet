"""
模組 C：Salary Competitiveness Detector
輸入整合模組 A（job_title、company_type、industry、seniority_level）
與模組 B（job_description_text）、模組 D（education_preference）
不需要 HR 額外填寫任何欄位。

處理流程：
  1. 規則層：從 job_description_text 解析 JD 是否已提供薪資範圍
  2. LLM 層：
     - 將 job_title 映射至勞動部職類別，取得職類薪資基準（平均數）
     - 將 industry 映射至主計總處產業分類，取得學歷與規模修正參考（中位數）
     - 綜合推估市場薪資區間（P25 / P75）
     - 對比 JD 薪資（若有）與市場區間，輸出競爭力判斷與建議

輸出欄位：
  - market_salary_range  : 市場薪資區間（P25 / P75，月薪元）
  - competitiveness_level: 競爭力等級（五級）
  - competitiveness_reason: 判斷理由
  - salary_suggestion    : 具體薪資建議
  - data_sources         : 本次推估實際引用的資料來源說明
  - confidence_level     : 推估可信度（high / medium / low）
  - confidence_reason    : 可信度說明
  - disclaimer           : 資料限制與使用提醒
"""

from pydantic import BaseModel, Field
from typing import Literal


# ── 合法選項定義 ──────────────────────────────────────────

CompetitivenessLevel = Literal[
    "高度競爭",
    "具競爭力",
    "普通",
    "偏低",
    "明顯偏低",
]

ConfidenceLevel = Literal["high", "medium", "low"]


# ── 輸入 Schema ───────────────────────────────────────────

class SalaryCheckRequest(BaseModel):
    """
    模組 C 的輸入資料結構。
    所有欄位來自上游模組的 session_state，HR 不需額外填寫。

    欄位來源：
    - 模組 A：job_title、company_type、industry、seniority_level、salary_min、salary_max
    - 模組 B：job_description_text（用於解析 JD 是否已提供薪資範圍）
    - 模組 D：education_level（學歷條件，對應主計總處學歷別統計）
    """
    # 從模組 A 帶入
    job_title: str = Field(
        ...,
        description="職稱，例：Python Backend Engineer。用於映射勞動部職類別"
    )
    company_type: str | None = Field(
        default=None,
        description="公司類型：startup / SME / enterprise。對應主計總處規模別統計"
    )
    industry: str | None = Field(
        default=None,
        description="產業，例：SaaS / 電商 / 金融。用於映射主計總處產業分類"
    )
    seniority_level: str | None = Field(
        default=None,
        description="年資層級：junior / mid / senior。影響薪資推估的調整方向"
    )
    salary_min: int | None = Field(
        default=None,
        description="JD 薪資下限（月薪，單位：元）。有填才與市場區間對比"
    )
    salary_max: int | None = Field(
        default=None,
        description="JD 薪資上限（月薪，單位：元）。有填才與市場區間對比"
    )

    # 從模組 B 帶入
    job_description_text: str = Field(
        ...,
        description="完整 JD 文字。規則層從中解析是否已提供薪資範圍，有則納入競爭力對比"
    )

    # 從模組 D 帶入
    education_level: Literal["不限", "大學", "碩士", "博士"] | None = Field(
        default=None,
        description="學歷要求等級，來自模組 D 的 education_preference.level。對應主計總處學歷別統計"
    )


# ── 輸出子結構 ────────────────────────────────────────────

class MarketSalaryRange(BaseModel):
    """
    LLM 推估的市場薪資區間。
    P25 / P75 為統計常用的四分位數表示法：
      - P25（第一四分位數）：市場上 25% 的人薪資低於此值，代表偏低的基準
      - P75（第三四分位數）：市場上 75% 的人薪資低於此值，代表較高的基準
    區間愈寬代表該職類薪資分佈愈分散。
    """
    p25_monthly: int = Field(
        ...,
        description="市場薪資第一四分位數（月薪，單位：元），低於此值代表薪資偏低"
    )
    p75_monthly: int = Field(
        ...,
        description="市場薪資第三四分位數（月薪，單位：元），高於此值代表薪資具競爭力"
    )
    median_monthly: int = Field(
        ...,
        description="市場薪資中位數估計（月薪，單位：元）"
    )


# ── 輸出 Schema ───────────────────────────────────────────

class SalaryCheckResponse(BaseModel):
    """
    模組 C 的輸出資料結構。
    前端可直接用各欄位渲染對應的 UI 區塊：
      - market_salary_range       → 薪資區間視覺化（例：數線或區間條）
      - competitiveness_level     → 競爭力等級標籤（五色標示）
      - competitiveness_reason    → 等級判斷理由段落
      - salary_suggestion         → 具體薪資建議段落
      - data_sources              → 資料來源說明（讓使用者知道推估依據）
      - confidence_level          → 可信度標籤
      - confidence_reason         → 可信度說明段落
      - disclaimer                → 資料限制提醒（固定顯示於頁面底部）
    """
    market_salary_range: MarketSalaryRange = Field(
        ...,
        description="LLM 推估的市場薪資區間（P25 / 中位數 / P75，月薪元）"
    )
    competitiveness_level: CompetitivenessLevel = Field(
        ...,
        description="薪資競爭力等級：高度競爭／具競爭力／普通／偏低／明顯偏低"
    )
    competitiveness_reason: str = Field(
        ...,
        description="競爭力判斷理由，60-100 字，說明為何落在此等級"
    )
    salary_suggestion: str = Field(
        ...,
        description="具體薪資建議，60-100 字，提供 HR 可參考的調整方向"
    )
    data_sources: str = Field(
        ...,
        description="本次推估實際引用的資料來源，例：勞動部職類別薪資調查（114年）、主計總處學歷別統計（113年）"
    )
    confidence_level: ConfidenceLevel = Field(
        ...,
        description="推估可信度：high（職稱與產業均能精確對應）/ medium（部分欄位需模糊映射）/ low（職稱或產業無法對應，僅能提供概估）"
    )
    confidence_reason: str = Field(
        ...,
        description="可信度說明，40-60 字，解釋影響可信度的關鍵因素"
    )
    disclaimer: str = Field(
        ...,
        description=(
            "資料限制與使用提醒，固定包含：資料年份（勞動部114年/主計總處113年）、"
            "統計方式差異（平均數 vs 中位數）、建議搭配 104 / LinkedIn 等即時平台驗證"
        )
    )