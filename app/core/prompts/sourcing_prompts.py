"""
模組 E：AI Sourcing Assistant — Prompt 層

- SYSTEM_PROMPT：角色設定與輸出格式，每次呼叫都帶著
- build_sourcing_prompt()：將 SourcingRequest 資料組裝成任務說明

移除 platform_recommendations：Boolean string 已涵蓋平台資訊，
不需要 LLM 另外推薦，減少 token 消耗並讓輸出更聚焦。
"""


from app.models.sourcing_schemas import SourcingRequest


SYSTEM_PROMPT = """
你是一位熟悉台灣招募市場的資深 TA（Talent Acquisition）顧問。
你的任務是根據職缺資訊與候選人 Persona，提供兩項輸出。

請嚴格按照以下 JSON 格式回傳，不要加任何說明文字或 markdown 標記：

{
  "outreach_message_template": "完整的破冰聯繫訊息，100字以內",
  "sourcing_tips": [
    "建議1",
    "建議2",
    "建議3"
  ]
}

輸出規則：
1. outreach_message_template：
   - 100 字以內
   - 通用破冰風格，目標是引起候選人興趣、讓對方願意回覆
   - 不針對特定平台，可用於 LinkedIn、CakeResume 或任何訊息管道
   - 語氣自然，避免制式感與銷售話術
   - 不要提到具體公司名稱或薪資數字
   - 結尾留一個開放式問句，引導對方回覆
2. sourcing_tips：提供 3 條實戰建議，每條 30–50 字
3. 所有內容使用繁體中文
4. 只回傳 JSON，不要加任何其他文字
"""


def build_sourcing_prompt(req: SourcingRequest) -> str:
    """
    將 SourcingRequest 的資料組裝成送給 LLM 的任務說明。

    設計原則：
    - 資料按重要性排列，最影響輸出品質的資訊放最前面
    - 選填欄位只在有值時才加入，避免送出無效資訊
    - 任務說明放最後，讓 LLM 在讀完所有資料後再看任務
    """
    lines = [
        "【職缺資訊】",
        f"職稱：{req.job_title}",
        f"理想年資：{req.ideal_seniority}",
        f"核心技能：{', '.join(req.key_skills)}",
    ]

    lines += [
        "",
        "【候選人 Persona】",
        f"常出現的平台：{', '.join(req.likely_channels)}",
        f"常見背景：{', '.join(req.likely_background)}",
        f"在意的面向：{', '.join(req.candidate_motivators)}",
        f"常見顧慮：{', '.join(req.likely_concerns)}",
        f"溝通偏好：{req.preferred_message_style}",
    ]

    if req.education_preference:
        edu = req.education_preference
        edu_line = f"學歷參考條件：{edu.level}"
        if edu.notes:
            edu_line += f"（{edu.notes}）"
        lines.append(edu_line)

    if req.additional_keywords:
        lines += [
            "",
            "【HR 補充資訊】",
            f"額外關鍵字：{', '.join(req.additional_keywords)}",
        ]

    if req.exclude_keywords:
        lines.append(f"排除詞彙：{', '.join(req.exclude_keywords)}")

    lines += [
        "",
        "【任務】",
        "根據以上資訊，請提供：",
        "1. 一封通用破冰聯繫訊息，引起候選人興趣，讓對方願意回覆",
        "2. 三條針對這個職缺與候選人特性的實戰 sourcing 建議",
    ]

    return "\n".join(lines)