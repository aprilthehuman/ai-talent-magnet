"""
模組 B：JD Rewrite AI — Service 層
核心邏輯：將 Company Profile 注入 prompt，對三種風格各呼叫一次 LLM，套用 Guardrail 後回傳

函式職責：
  - build_prompt()：將 CompanyProfile 欄位與風格指令組裝成完整 prompt
  - check_must_avoid()：Guardrail 後處理，掃描 LLM 輸出是否含有禁用詞
  - rewrite_jd()：主函式，串聯以上兩個函式，回傳三種風格的改寫結果

Guardrail 設計：
  - must_avoid：後處理掃描，違規時在輸出文末附上警告，提示 HR 手動修改
  - must_include：注入 prompt，由 LLM 負責自然融入改寫結果
"""


import os
from openai import OpenAI
from dotenv import load_dotenv
from app.models.rewriter_schemas import RewriteJDRequest, RewriteJDResponse


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def build_prompt(original_jd: str, profile, style: str, target_candidate_focus: str | None) -> str:
    """
    組裝單一風格的 prompt
    style: "startup" / "stable_enterprise" / "high_growth"
    """

    style_instructions = {
        "startup": "改寫成「Startup 風」：強調 ownership、影響力、快速成長, 語氣直接、熱血、重視自主性",
        "stable_enterprise": "改寫成「穩定企業風」：強調制度、福利、穩定發展、團隊支持，語氣溫暖、專業、重視保障",
        "high_growth": "改寫成「高成長挑戰型」：強調學習、挑戰、技術深度、快速升級，語氣充滿野心、啟發性、重視成長"
    }

    # 將 list 欄位轉成中文頓號串接的字串，方便帶入 prompt
    culture_str = "、".join(profile.culture_keywords)
    must_include_str = "、".join(profile.must_include) if profile.must_include else "（無）"
    must_avoid_str = "、".join(profile.must_avoid) if profile.must_avoid else "（無）"
    target_str = f"想吸引的候選人特質：{target_candidate_focus}\n" if target_candidate_focus else ""

    prompt = f"""你是一位熟悉台灣招募市場的 HR 顧問。

【公司背景】
公司名稱：{profile.company_name}
企業文化關鍵字：{culture_str}
公司願景：{profile.vision}
主管風格：{profile.manager_style or "（未提供）"}
語氣偏好：{profile.tone_preference or "（未提供）"}
產業背景：{profile.industry_context or "（未提供）"}
必須帶到的訊息：{must_include_str}
絕對不可出現的詞：{must_avoid_str}
{target_str}

【改寫規則】
1. {style_instructions[style]}
2. 語氣必須符合上述公司背景
3. 必帶訊息要自然融入 JD，不可直接複製貼上
4. 不可捏造原文沒有的福利、薪資、股票資訊
5. 不可改變職務核心職責
6. 務必避開 must_avoid 清單中的所有詞彙

【原始 JD】
{original_jd}

請直接輸出改寫後的完整 JD，不要加任何說明文字。"""

    return prompt


def check_must_avoid(text: str, must_avoid: list[str]) -> list[str]:
    """
    Guardrail: 掃描輸出是否含有禁用詞
    回傳：出現的禁用詞清單（空 list 代表通過）
    """
    return [word for word in must_avoid if word in text]


def rewrite_jd(request: RewriteJDRequest) -> RewriteJDResponse:
    """
    模組 B 主函式：對三種風格各呼叫一次 OpenAI, 套用 Guardrail 後回傳
    """
    profile = request.company_profile
    styles = ["startup", "stable_enterprise", "high_growth"]
    results = {}

    for style in styles:
        # 依風格組裝 prompt
        prompt = build_prompt(
            original_jd=request.original_jd,
            profile=profile,
            style=style,
            target_candidate_focus=request.target_candidate_focus
        )

        # 呼叫 OpenAI API，temperature 0.7 給予較多創意空間
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        output_text = response.choices[0].message.content.strip()

        # Guardrail：若輸出含有禁用詞，在文末加上警告提示
        violations = check_must_avoid(output_text, profile.must_avoid)
        if violations:
            output_text += f"\n\n⚠️ 注意：以下禁用詞仍出現在輸出中，請手動修改：{violations}"

        results[style] = output_text

    # 組裝每個版本的改寫重點說明
    rewrite_notes = [
        "Startup 風：強調 ownership 與快速成長，語氣直接熱血，適合吸引有創業精神的候選人",
        "穩定企業風：強調制度與福利保障，語氣溫暖專業，適合吸引重視穩定的候選人",
        "高成長挑戰型：強調技術深度與學習機會，語氣充滿野心，適合吸引追求快速成長的候選人"
    ]

    # 組裝 profile_applied 摘要，讓使用者可驗證系統實際套用了哪些設定
    profile_applied = {
        "company_name": profile.company_name,
        "culture_keywords": profile.culture_keywords,
        "must_include": profile.must_include,
        "must_avoid": profile.must_avoid,
        "tone_preference": profile.tone_preference
    }

    return RewriteJDResponse(
        startup_version=results["startup"],
        stable_enterprise_version=results["stable_enterprise"],
        high_growth_version=results["high_growth"],
        rewrite_notes=rewrite_notes,
        profile_applied=profile_applied
    )