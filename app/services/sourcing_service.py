import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from app.models.sourcing_schemas import SourcingRequest, SourcingResult, PlatformRecommendation
from app.core.keyword_dicts import TITLE_SYNONYMS, TITLE_SYNONYMS_REVERSE
from app.core.prompts import sourcing_prompts


"""
模組 E：AI Sourcing Assistant — Service 層

負責所有商業邏輯，分為兩類處理方式：
  1. 純 Python 邏輯（不呼叫 LLM，快速且成本為零）：
     - expand_titles()：查同義詞字典展開職稱，字典找不到時 fallback 到 LLM
     - build_boolean_strings()：三段式 Boolean string 組裝

  2. LLM 生成（呼叫 OpenAI API，與模組 A、B、D 相同的初始化方式）：
     - expand_titles_with_llm()：字典 fallback，生成職稱同義詞
     - generate_llm_content()：一次生成平台推薦、Outreach 訊息、sourcing tips

主函式 generate_sourcing_result() 統籌呼叫以上兩類，組裝成完整的 SourcingResult。
"""


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ── 1. LLM Fallback：字典找不到時使用 ───────────────────

def expand_titles_with_llm(job_title: str) -> list[str]:
    """
    字典查不到對應職稱時的 fallback。
    請 LLM 針對輸入的職稱，生成台灣市場常用的同義詞清單（含中英文）。

    為什麼用 temperature=0：
    職稱同義詞是固定的業界慣例，不需要創意發揮，
    temperature=0 讓每次輸入相同職稱時結果一致，方便測試與除錯。

    為什麼用 try/except 包住整段：
    LLM 偶爾會回傳空字串、格式錯誤的 JSON、或非預期的結構，
    直接 json.loads() 會讓整個請求崩潰。
    用 try/except 確保最差情況只是回傳原始職稱，不影響後續流程。
    """
    
    prompt = f"""
        請列出「{job_title}」在台灣職場中常見的同義職稱，包含中文和英文。
        只回傳 JSON object，格式如下，不要加任何說明文字或 markdown 標記：
        {{"titles": ["職稱A", "職稱B", "職稱C"]}}
        最多列 6 個。
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)

        if isinstance(result, dict) and "titles" in result:
            return result["titles"]

    except Exception:
        # LLM 呼叫失敗、JSON 解析失敗、格式不符，一律 fallback 回原始職稱
        pass

    return [job_title]


# ── 2. 職稱同義展開 ───────────────────────────────────────

def expand_titles(job_title: str) -> list[str]:
    """
    將輸入的職稱展開為台灣市場常用的同義詞清單。

    查詢順序（優先度由高到低）：
      1. 反向索引完整比對：例如輸入「人資」直接命中
      2. 正向字典完整比對：例如輸入「hr」直接命中
      3. 部分比對：例如輸入「Python Backend Engineer」包含「backend engineer」
      4. LLM fallback：以上都找不到，讓 LLM 即時生成

    為什麼最後用 dict.fromkeys() 去重複：
    字典裡的同義詞或 LLM 生成的結果可能有重複項目，
    例如 ["Backend Engineer", "Backend Engineer", "後端工程師"]。
    dict.fromkeys() 去重複的同時保留原始順序，
    避免 Boolean string 出現重複的職稱項目。
    """
    key = job_title.lower()

    # 步驟 1：查反向索引（處理同義詞輸入，例如「人資」→ "hr" → 完整清單）
    if key in TITLE_SYNONYMS_REVERSE:
        canonical_key = TITLE_SYNONYMS_REVERSE[key]
        synonyms = TITLE_SYNONYMS[canonical_key]
        return list(dict.fromkeys(synonyms))

    # 步驟 2：正向完整比對
    if key in TITLE_SYNONYMS:
        synonyms = TITLE_SYNONYMS[key]
        return list(dict.fromkeys(synonyms))

    # 步驟 3：部分比對（例如輸入「Python Backend Engineer」包含「backend engineer」）
    for dict_key, synonyms in TITLE_SYNONYMS.items():
        if dict_key in key:
            return list(dict.fromkeys(synonyms))

    # 步驟 4：字典完全找不到 → LLM fallback
    result = expand_titles_with_llm(job_title)
    return list(dict.fromkeys(result))


# ── 3. Boolean String 組裝 ────────────────────────────────

def build_boolean_strings(
    job_title: str,
    expanded_titles: list[str],
    key_skills: list[str],
    exclude_keywords: list[str],
    additional_keywords: list[str],
) -> dict[str, str]:
    """
    三段式 Boolean string 組裝，針對三個平台各自產生對應語法。

    三段式結構：
      段落 1（職稱段）：expanded_titles 用 OR 連接，加括號包住
      段落 2（技能段）：key_skills 前三個 + additional_keywords 用 AND 連接
      段落 3（排除段）：exclude_keywords 用 NOT 連接

    三個平台的差異：
      LinkedIn   → 標準 Boolean，英文職稱加引號，支援完整 AND/OR/NOT
      CakeResume → 簡化版，中文職稱優先，不加引號（平台不支援）
      Google     → X-Ray 語法，加上 site:linkedin.com/in 縮小搜尋範圍

    為什麼技能只取前三個：
    Boolean string 過長會超過搜尋引擎字數上限（LinkedIn 約 1000 字元），
    前三個核心技能已足夠縮小搜尋範圍，其餘靠人工篩選。

    為什麼技能段要判斷是否為空：
    如果 key_skills 和 additional_keywords 都是空 list，
    直接拼接會產生「("Backend Engineer") AND 」這樣的非法 Boolean 語法，
    搜尋引擎會報錯或回傳非預期結果。
    """
    # 將同義詞按語言分類，給不同平台使用
    english_titles = [
        t for t in expanded_titles
        if not any('\u4e00' <= c <= '\u9fff' for c in t)
    ]
    chinese_titles = [
        t for t in expanded_titles
        if any('\u4e00' <= c <= '\u9fff' for c in t)
    ]

    # 技能段：最多取前三個核心技能，加上 HR 補充的關鍵字
    top_skills = key_skills[:3]
    all_keywords = top_skills + additional_keywords

    # 排除段：每個詞前面加 NOT
    exclude_part = " ".join([f'NOT "{kw}"' for kw in exclude_keywords])

    # ── LinkedIn：英文職稱加引號，標準 Boolean 語法 ──
    title_part_linkedin = "(" + " OR ".join(
        [f'"{t}"' for t in english_titles]
    ) + ")"
    linkedin = title_part_linkedin
    if all_keywords:
        skill_part_linkedin = " AND ".join([f'"{s}"' for s in all_keywords])
        linkedin += f" AND {skill_part_linkedin}"
    if exclude_part:
        linkedin += f" {exclude_part}"

    # ── CakeResume：中文職稱優先，不加引號 ──
    cake_titles = chinese_titles if chinese_titles else english_titles
    title_part_cake = " OR ".join(cake_titles)
    cake = f"({title_part_cake})"
    if all_keywords:
        skill_part_cake = " ".join(all_keywords)
        cake += f" {skill_part_cake}"
    if exclude_part:
        cake += f" {exclude_part}"

    # ── Google X-Ray：site: 限定 LinkedIn，職稱和技能加引號 ──
    google = f'site:linkedin.com/in "{job_title}"'
    if top_skills:
        xray_skills = " ".join([f'"{s}"' for s in top_skills])
        google += f" {xray_skills}"

    return {
        "linkedin": linkedin,
        "cake": cake,
        "google": google,
    }


# ── 4. LLM 生成：平台推薦、Outreach 訊息、Sourcing Tips ──

def generate_llm_content(req: SourcingRequest) -> dict:
    """
    一次呼叫 LLM，同時生成三個輸出：
      - platform_recommendations：平台推薦清單（含推薦理由與適用程度）
      - outreach_message_template：個人化主動聯繫訊息
      - sourcing_tips：針對此職缺的實戰 sourcing 建議

    為什麼三個合併成一次呼叫：
    每次 API 呼叫都有固定的網路延遲，三次呼叫的等待時間會累加。
    合併成一次可以減少延遲，同時也降低 API 費用。

    與模組 B、D 一致，使用 response_format json_object 確保回傳結構化 JSON。
    """
    prompt = sourcing_prompts.build_sourcing_prompt(req)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sourcing_prompts.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    return json.loads(raw)


# ── 5. 主函式 ─────────────────────────────────────────────

def generate_sourcing_result(req: SourcingRequest) -> SourcingResult:
    """
    Module E 的主要進入點，供 router 呼叫。

    執行順序：
      1. expand_titles()：純 Python 為主，字典找不到才 fallback 到 LLM
      2. build_boolean_strings()：純 Python，不需要等待
      3. generate_llm_content()：呼叫 LLM，等待時間最長放最後

    與模組 B、D 相同，全部使用同步函式（def，非 async def）。

    為什麼用 .get() 取 platform_recommendations：
    LLM 偶爾會回傳 key 名稱不符預期的 JSON（例如 "platforms" 而非 "platform_recommendations"），
    直接用 llm_output["platform_recommendations"] 會拋出 KeyError 讓整個請求失敗。
    .get() 加上預設空 list，確保就算 LLM 格式跑掉，前端還是能收到部分結果。
    """
    # 步驟 1：職稱同義展開
    expanded_titles = expand_titles(req.job_title)

    # 步驟 2：Boolean string 組裝（純 Python）
    boolean_strings = build_boolean_strings(
        job_title=req.job_title,
        expanded_titles=expanded_titles,
        key_skills=req.key_skills,
        exclude_keywords=req.exclude_keywords,
        additional_keywords=req.additional_keywords,
    )

    # 步驟 3：LLM 生成（最慢，放最後）
    llm_output = generate_llm_content(req)

    # 用 .get() 防止 LLM 回傳非預期 key 名稱時直接崩潰
    platform_data = llm_output.get("platform_recommendations", [])

    # 組裝成 SourcingResult 回傳
    return SourcingResult(
        expanded_titles=expanded_titles,
        boolean_string_linkedin=boolean_strings["linkedin"],
        boolean_string_cake=boolean_strings["cake"],
        boolean_string_google=boolean_strings["google"],
        platform_recommendations=[
            PlatformRecommendation(**p)
            for p in platform_data
        ],
        outreach_message_template=llm_output.get("outreach_message_template", ""),
        sourcing_tips=llm_output.get("sourcing_tips", []),
    )