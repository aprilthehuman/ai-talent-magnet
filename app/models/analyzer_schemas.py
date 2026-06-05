from pydantic import BaseModel

"""
1. 匯入建立資料模型需要的工具(BaseModel)
2. 建立 API 接收用的輸入格式(AnalyzeJDRequest), 包含職稱、JD 文字、以及三個 AI 層選填欄位
3. 建立 API 回傳用的輸出格式(AnalyzeJDResponse), 包含分數、等級標籤、語氣分析、關鍵字偵測結果與改善建議
4. 讓 FastAPI 可以自動驗證資料、產生文件、整理 JSON 結構
"""

# 模組 A 的輸入格式
class AnalyzeJDRequest(BaseModel):
    job_title: str
    job_description_text: str
    company_type: str | None = None
    industry: str | None = None
    seniority_level: str | None = None


# 模組 A 的輸出格式
class AnalyzeJDResponse(BaseModel):
    attraction_score: int
    score_label: str
    tone_analysis: str
    negative_keywords_detected: list[str]
    vague_phrases_detected: list[str]
    missing_elements: list[str]
    improvement_suggestions: list[str]