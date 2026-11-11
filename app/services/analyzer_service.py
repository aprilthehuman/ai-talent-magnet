"""
模組 A：JD Attraction Analyzer — Service 層
核心邏輯：規則層 + AI 層混合評分，計算 JD 吸引力分數

規則層（扣分，無上限）：
  - detect_negative_keywords()：掃描負面詞彙，每個扣 5 分
  - detect_vague_phrases()：掃描模糊用語，每個扣 3 分
  - detect_missing_elements()：檢查四項缺失資訊（薪資 -10、工作內容 -10、
    成長機會 -8、團隊文化 -5），薪資另以正規表達式辨識「數字+K」

AI 層（加分，0–40 分）：
  - analyze_tone_with_ai()：呼叫 LLM 分析語氣整體感受，產出分數、描述與改善建議

最終分數公式：min(100, max(0, 60 + AI層分數 - 規則層總扣分))
底分 60，扣分不封頂，最後夾在 0–100 之間。
"""


import os
import re
import json
from openai import OpenAI
from dotenv import load_dotenv
from app.core.keyword_dicts import (
    NEGATIVE_KEYWORDS,
    VAGUE_PHRASES,
    MISSING_CHECKLIST,
    MISSING_PENALTY,
    MISSING_REGEX
)
from app.models.analyzer_schemas import AnalyzeJDRequest, AnalyzeJDResponse, MissingElement


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def detect_negative_keywords(text: str) -> list[str]:
    """掃描 JD 裡有沒有負面詞彙"""
    # 先找出所有命中的詞
    found = [kw for kw in NEGATIVE_KEYWORDS if kw in text]

    # 去重：若短詞是已命中長詞的一部分（例如「抗壓」⊂「抗壓性高」），
    # 只保留長詞，避免同一句話被扣兩次分
    found = [
        kw for kw in found
        if not any(kw != other and kw in other for other in found)
    ]
    return found


def detect_vague_phrases(text: str) -> list[str]:
    """掃描 JD 裡有沒有模糊用語"""
    found = []
    for phrase in VAGUE_PHRASES:
        if phrase in text:
            found.append(phrase)
    return found


def detect_missing_elements(text: str) -> tuple[list[MissingElement], int]:
    """
    檢查 JD 缺少哪些重要資訊
    回傳：(缺失項目清單, 總扣分)
    """
    missing = []
    total_penalty = 0

    for category, keywords in MISSING_CHECKLIST:
        # 第一關：關鍵字比對
        has_category = any(kw in text for kw in keywords)

        # 第二關：關鍵字沒中時，再用正規表達式檢查（目前只有薪資用到）
        if not has_category:
            patterns = MISSING_REGEX.get(category, [])
            has_category = any(re.search(p, text) for p in patterns)

        if not has_category:
            penalty = MISSING_PENALTY[category]["score"]
            label = MISSING_PENALTY[category]["label"]
            missing.append(MissingElement(label=label, penalty=penalty))
            total_penalty += penalty

    return missing, total_penalty


def analyze_tone_with_ai(
    job_title: str,
    text: str,
    company_type: str = None,
    industry: str = None,
    seniority_level: str = None
) -> tuple[int, str, list[str]]:
    """
    用 LLM 分析 JD 語氣
    回傳：(AI層分數, 語氣描述, 改善建議)
    """
    # 把選填欄位組成背景資訊，沒填的就不帶進 prompt
    context_parts = []
    if company_type:
        context_parts.append(f"公司類型：{company_type}")
    if industry:
        context_parts.append(f"產業：{industry}")
    if seniority_level:
        context_parts.append(f"年資層級：{seniority_level}")

    context_str = "\n".join(context_parts) if context_parts else "（未提供）"

    prompt = f"""
你是一位資深招募顧問，請從「候選人角度」分析以下職缺描述（JD）。

職稱：{job_title}
{context_str}
JD 內容：
{text}

請用以下 JSON 格式回答，不要加任何其他文字：
{{
  "tone_score": 分數（0到40之間的整數）,
  "tone_description": "請用80到100字描述這份JD的整體語氣，需涵蓋：語氣風格、對候選人的吸引力程度、以及整體給人的感受",
  "top_3_improvements": [
    "【問題】說明具體問題在哪（約30字）→【原因】為什麼這樣寫會讓候選人卻步（約30字）→【建議】具體怎麼改（約50字）",
    "【問題】說明具體問題在哪（約30字）→【原因】為什麼這樣寫會讓候選人卻步（約30字）→【建議】具體怎麼改（約50字）",
    "【問題】說明具體問題在哪（約30字）→【原因】為什麼這樣寫會讓候選人卻步（約30字）→【建議】具體怎麼改（約50字）"
  ]
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.5
    )

    result = json.loads(response.choices[0].message.content)

    # 防呆：不管 AI 回傳什麼，都夾在 0~40 之間
    # int() 順便處理 AI 回傳 "35" 字串的情況
    tone_score = max(0, min(40, int(result["tone_score"])))

    return (
        tone_score,
        result["tone_description"],
        result["top_3_improvements"]
    )


def get_score_label(score: int) -> str:
    """根據分數回傳對應的等級標籤"""
    if score >= 80:
        return "優良"
    elif score >= 60:
        return "普通"
    elif score >= 40:
        return "偏低"
    else:
        return "危險"


def analyze_jd(request: AnalyzeJDRequest) -> AnalyzeJDResponse:
    """
    模組 A 的主函式：整合規則層 + AI 層，計算吸引力分數
    """
    text = request.job_description_text

    # 規則層
    negative_found = detect_negative_keywords(text)
    vague_found = detect_vague_phrases(text)
    missing, missing_penalty = detect_missing_elements(text)

    # AI 層
    tone_score, tone_desc, suggestions = analyze_tone_with_ai(
        job_title=request.job_title,
        text=text,
        company_type=request.company_type,
        industry=request.industry,
        seniority_level=request.seniority_level
    )

    # 計算最終分數
    negative_penalty = len(negative_found) * 5
    vague_penalty = len(vague_found) * 3
    total_deduction = negative_penalty + vague_penalty + missing_penalty

    final_score = min(100, max(0, 60 + tone_score - total_deduction))

    return AnalyzeJDResponse(
        attraction_score=final_score,
        tone_score=tone_score,
        score_label=get_score_label(final_score),
        tone_analysis=tone_desc,
        negative_keywords_detected=negative_found,
        vague_phrases_detected=vague_found,
        missing_elements=missing,
        improvement_suggestions=suggestions
    )