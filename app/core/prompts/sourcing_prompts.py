"""
模組 E：AI Sourcing Assistant — Prompt 層

集中管理所有送給 LLM 的指令，分為兩個部分：
  - SYSTEM_PROMPT：固定的角色設定與輸出格式要求，每次呼叫都帶著
  - build_sourcing_prompt()：將 SourcingRequest 的實際資料組裝成任務說明

為什麼輸出格式要在 SYSTEM_PROMPT 裡定義：
讓 LLM 從一開始就知道要回傳什麼結構，
比在 user prompt 最後才說「請回傳 JSON」更穩定，
因為 system 層級的指令優先度比 user 層級高。
"""


from app.models.sourcing_schemas import SourcingRequest


# ── System Prompt ─────────────────────────────────────────

SYSTEM_PROMPT = """
你是一位熟悉台灣招募市場的資深 TA（Talent Acquisition）顧問。
你的任務是根據職缺資訊與候選人 Persona，提供三項 sourcing 建議。

請嚴格按照以下 JSON 格式回傳，不要加任何說明文字或 markdown 標記：

{
  "platform_recommendations": [
    {
      "platform": "平台名稱",
      "suitability": "高 / 中 / 低 （三選一）",
      "reason": "推薦理由，50字以內",
      "search_url_hint": "搜尋入口提示，若無則填 null"
    }
  ],
  "outreach_message_template": "完整的 LinkedIn InMail 訊息，150字以內",
  "sourcing_tips": [
    "建議1",
    "建議2",
    "建議3"
  ]
}

輸出規則：
1. platform_recommendations 必須包含 3–5 個平台
2. outreach_message_template 不超過 150 字，語氣自然，避免制式感
3. sourcing_tips 提供 3 條實戰建議，每條 30–50 字
4. 所有內容使用繁體中文
5. 只回傳 JSON，不要加任何其他文字
"""


# ── User Prompt 組裝 ──────────────────────────────────────

def build_sourcing_prompt(req: SourcingRequest) -> str:
    """
    將 SourcingRequest 的資料組裝成送給 LLM 的任務說明。

    設計原則：
    - 資料按「重要性」排列，最影響輸出品質的資訊放最前面
    - 選填欄位（education_preference、additional_keywords 等）
      只在有值時才加入 prompt，避免送出「學歷要求：無」這類無效資訊
      讓 LLM 產生不必要的回應
    - 每個區塊用標題分隔，讓 LLM 更容易解析各段資訊的用途
    """

    # ── 基本職缺資訊 ──
    lines = [
        "【職缺資訊】",
        f"職稱：{req.job_title}",
        f"理想年資：{req.ideal_seniority}",
        f"核心技能：{', '.join(req.key_skills)}",
    ]

    # ── 候選人 Persona（影響 Outreach 訊息和平台推薦的關鍵資料）──
    lines += [
        "",
        "【候選人 Persona】",
        f"常出現的平台：{', '.join(req.likely_channels)}",
        f"常見背景：{', '.join(req.likely_background)}",
        f"在意的面向：{', '.join(req.candidate_motivators)}",
        f"常見顧慮：{', '.join(req.likely_concerns)}",
        f"溝通偏好：{req.preferred_message_style}",
    ]

    # ── 學歷條件（選填，有值才加入）──
    if req.education_preference:
        edu = req.education_preference
        edu_line = f"學歷參考條件：{edu.level}"
        if edu.notes:
            edu_line += f"（{edu.notes}）"
        lines.append(edu_line)

    # ── HR 補充關鍵字（選填，有值才加入）──
    if req.additional_keywords:
        lines += [
            "",
            "【HR 補充資訊】",
            f"額外關鍵字：{', '.join(req.additional_keywords)}",
        ]

    if req.exclude_keywords:
        lines.append(f"排除詞彙：{', '.join(req.exclude_keywords)}")

    # ── 任務說明（放最後，讓 LLM 在讀完所有資料後再看任務）──
    lines += [
        "",
        "【任務】",
        "根據以上資訊，請提供：",
        "1. 針對這個職缺與候選人特性的平台推薦（含推薦理由）",
        "2. 一封符合候選人溝通偏好的 LinkedIn InMail 主動聯繫訊息",
        "3. 三條針對這個職缺的實戰 sourcing 建議",
    ]

    return "\n".join(lines)