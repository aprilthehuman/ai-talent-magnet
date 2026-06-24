"""
模組 D 核心邏輯：
1. 組裝 prompt (注入模組 B 的 Company Profile + 選定 JD + 模組 A 的背景欄位 + 學歷參考條件)
2. 呼叫 OpenAI API, 使用 response_format 強制回傳結構化 JSON (與模組 A 一致)
3. 解析回傳的 JSON, 對應到 CandidatePersona schema
"""


import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from app.models.persona_schemas import (
    GeneratePersonaRequest,
    GeneratePersonaResponse,
    CandidatePersona
)


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_persona(request: GeneratePersonaRequest) -> GeneratePersonaResponse:

    # 組裝模組 A 的背景欄位
    context_parts = []
    if request.company_type:
        context_parts.append(f"公司類型：{request.company_type}")
    if request.industry:
        context_parts.append(f"產業：{request.industry}")
    if request.seniority_level:
        context_parts.append(f"年資層級：{request.seniority_level}")
    context_str = "\n".join(context_parts) if context_parts else "（未提供）"

    # 組裝學歷參考條件
    edu = request.education_preference
    if edu:
        edu_str = f"學歷參考條件：{edu.level}"
        if edu.notes:
            edu_str += f"（{edu.notes}）"
    else:
        edu_str = "學歷參考條件：不限"

    # 組裝模組 B 的 Company Profile
    profile = request.company_profile
    culture_str = "、".join(profile.culture_keywords)
    must_include_str = "、".join(profile.must_include) if profile.must_include else "（無）"
    must_avoid_str = "、".join(profile.must_avoid) if profile.must_avoid else "（無）"
    target_str = f"\n想吸引的候選人特質：{request.target_candidate_focus}" if request.target_candidate_focus else ""

    prompt = f"""你是一位熟悉台灣科技業招募市場的資深 HR 顧問。

    請根據以下資訊，從「候選人視角」反推出這個職缺最可能吸引到的理想候選人樣貌。

    【職缺背景】
    職稱：{request.job_title}
    {context_str}
    {edu_str}（作為參考，非硬性要求，反映在 likely_background 的描述中即可）

    【公司背景】
    公司名稱：{profile.company_name}
    企業文化關鍵字：{culture_str}
    公司願景：{profile.vision}
    主管風格：{profile.manager_style or "（未提供）"}
    語氣偏好：{profile.tone_preference or "（未提供）"}
    必須帶到的訊息：{must_include_str}
    絕對不可出現的詞：{must_avoid_str}
    {target_str}

    【職缺描述（已根據公司背景改寫）】
    {request.job_description_text}

    請用以下 JSON 格式回答，不要加任何其他文字：
    {{
        "ideal_seniority": "理想年資區間，例：3–5 年",
        "likely_background": ["2–4 條可能的職涯背景描述，反映學歷參考條件"],
        "key_skills": ["4–6 個核心技能"],
        "candidate_motivators": ["3–5 個這類候選人在意的面向"],
        "likely_concerns": ["2–4 個可能的顧慮"],
        "preferred_message_style": "建議 HR 和這類候選人溝通時的語氣風格，一句話說明",
        "likely_channels": ["2–4 個這類候選人常出現的平台"]
    }}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.5
    )

    result = json.loads(response.choices[0].message.content)
    persona = CandidatePersona(**result)

    return GeneratePersonaResponse(
        job_title=request.job_title,
        persona=persona,
        education_preference=request.education_preference  # 原樣帶出供 Module E 接收
    )