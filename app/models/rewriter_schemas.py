from pydantic import BaseModel

"""
1. 匯入建立資料模型需要的工具(BaseModel)
2. 建立巢狀物件 CompanyProfile, 描述公司文化、願景、改寫規則
3. 建立 API 接收用的輸入格式(RewriteJDRequest), 包含原始 JD 與巢狀的 CompanyProfile
4. 建立 API 回傳用的輸出格式(RewriteJDResponse), 包含三種風格的改寫結果
5. 讓 FastAPI 可以自動驗證巢狀資料結構、產生文件、整理 JSON 格式
"""

class CompanyProfile(BaseModel):
    company_name: str
    culture_keywords: list[str]
    vision: str
    manager_style: str | None = None
    tone_preference: str | None = None
    must_include: list[str] = []
    must_avoid: list[str] = []
    industry_context: str | None = None


class RewriteJDRequest(BaseModel):
    original_jd: str
    company_profile: CompanyProfile
    target_candidate_focus: str | None = None


class RewriteJDResponse(BaseModel):
    startup_version: str
    stable_enterprise_version: str
    high_growth_version: str
    rewrite_notes: list[str]    # 3 條，每個版本一條說明
    profile_applied: dict       # 套用的 Profile 摘要，供驗證用
    