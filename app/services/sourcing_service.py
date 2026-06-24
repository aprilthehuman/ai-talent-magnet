"""
模組 E：AI Sourcing Assistant — Service 層

負責所有商業邏輯，分為兩類處理方式：
  1. 純 Python 邏輯（不呼叫 LLM）：
     - expand_titles()：查同義詞字典展開職稱，字典找不到時 fallback 到 LLM
     - build_boolean_strings()：五種平台搜尋語法組裝

  2. LLM 生成：
     - expand_titles_with_llm()：字典 fallback
     - generate_llm_content()：生成 Outreach 訊息與 sourcing tips
"""


import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from app.models.sourcing_schemas import SourcingRequest, SourcingResult
from app.core.keyword_dicts import TITLE_SYNONYMS, TITLE_SYNONYMS_REVERSE
from app.core.prompts import sourcing_prompts


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ── 1. LLM Fallback：字典找不到時使用 ───────────────────

def expand_titles_with_llm(job_title: str) -> list[str]:
    """
    字典查不到對應職稱時的 fallback。
    temperature=0 確保同一職稱每次輸入結果一致。
    try/except 確保 LLM 失敗時不影響後續流程。
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
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)
        if isinstance(result, dict) and "titles" in result:
            return result["titles"]
    except Exception:
        pass

    return [job_title]


# ── 2. 職稱同義展開 ───────────────────────────────────────

def expand_titles(job_title: str) -> list[str]:
    """
    查詢順序：反向索引 → 正向完整比對 → 部分比對 → LLM fallback。
    每個回傳路徑都用 dict.fromkeys() 去重複並保留順序。
    """
    key = job_title.lower()

    if key in TITLE_SYNONYMS_REVERSE:
        canonical_key = TITLE_SYNONYMS_REVERSE[key]
        return list(dict.fromkeys(TITLE_SYNONYMS[canonical_key]))

    if key in TITLE_SYNONYMS:
        return list(dict.fromkeys(TITLE_SYNONYMS[key]))

    for dict_key, synonyms in TITLE_SYNONYMS.items():
        if dict_key in key:
            return list(dict.fromkeys(synonyms))

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
    五種平台搜尋語法組裝：

    區塊一 LinkedIn：
      - linkedin：LinkedIn 內建 Boolean（英文職稱 + 技能 + 排除）
      - google_linkedin：Google X-Ray 搜尋 LinkedIn 公開頁面

    區塊二 CakeResume：
      - cake：CakeResume 內建搜尋（中文職稱優先，不加引號）
      - google_cake：Google X-Ray 搜尋 CakeResume 履歷頁面

    區塊三 104：
      - google_104：Google X-Ray 搜尋 104（主動搜尋履歷需企業付費帳號）

    為什麼技能只取前三個：
    Boolean string 過長會超過搜尋引擎字數上限，
    前三個核心技能已足夠縮小搜尋範圍。

    為什麼技能段要判斷是否為空：
    空技能段會產生「("Backend Engineer") AND 」非法語法。
    """
    # 中英文職稱分類
    english_titles = [
        t for t in expanded_titles
        if not any('\u4e00' <= c <= '\u9fff' for c in t)
    ]
    chinese_titles = [
        t for t in expanded_titles
        if any('\u4e00' <= c <= '\u9fff' for c in t)
    ]

    top_skills = key_skills[:3]
    all_keywords = top_skills + additional_keywords
    exclude_part = " ".join([f'NOT "{kw}"' for kw in exclude_keywords])

    # ── LinkedIn 內建 ──
    title_part_linkedin = "(" + " OR ".join(
        [f'"{t}"' for t in english_titles]
    ) + ")"
    linkedin = title_part_linkedin
    if all_keywords:
        skill_part = " AND ".join([f'"{s}"' for s in all_keywords])
        linkedin += f" AND {skill_part}"
    if exclude_part:
        linkedin += f" {exclude_part}"

    # ── Google X-Ray → LinkedIn ──
    google_linkedin = f'site:linkedin.com/in "{job_title}"'
    if top_skills:
        google_linkedin += " " + " ".join([f'"{s}"' for s in top_skills])

    # ── CakeResume 內建 ──
    cake_titles = chinese_titles if chinese_titles else english_titles
    cake = "(" + " OR ".join(cake_titles) + ")"
    if all_keywords:
        cake += " " + " ".join(all_keywords)
    if exclude_part:
        cake += f" {exclude_part}"

    # ── Google X-Ray → CakeResume ──
    google_cake = f'site:cakeresume.com/resumes "{job_title}"'
    if top_skills:
        google_cake += " " + " ".join([f'"{s}"' for s in top_skills])

    # ── Google X-Ray → 104 ──
    # 104 不支援 Boolean 語法，用職稱和核心技能做關鍵字搜尋即可
    google_104 = f'site:104.com.tw "{job_title}"'
    if top_skills:
        google_104 += " " + " ".join([f'"{s}"' for s in top_skills])

    return {
        "linkedin": linkedin,
        "google_linkedin": google_linkedin,
        "cake": cake,
        "google_cake": google_cake,
        "google_104": google_104,
    }


# ── 4. LLM 生成：Outreach 訊息 + Sourcing Tips ───────────

def generate_llm_content(req: SourcingRequest) -> dict:
    """
    一次呼叫 LLM，生成兩個輸出：
      - outreach_message_template：通用破冰聯繫訊息
      - sourcing_tips：實戰 sourcing 建議

    移除 platform_recommendations，因為 Boolean string 已涵蓋平台資訊，
    不需要 LLM 再另外推薦平台，減少 API token 消耗。
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
      1. expand_titles()：職稱同義展開
      2. build_boolean_strings()：五種平台語法組裝（純 Python）
      3. generate_llm_content()：Outreach 訊息 + sourcing tips
    """
    expanded_titles = expand_titles(req.job_title)

    boolean_strings = build_boolean_strings(
        job_title=req.job_title,
        expanded_titles=expanded_titles,
        key_skills=req.key_skills,
        exclude_keywords=req.exclude_keywords,
        additional_keywords=req.additional_keywords,
    )

    llm_output = generate_llm_content(req)

    return SourcingResult(
        expanded_titles=expanded_titles,
        boolean_string_linkedin=boolean_strings["linkedin"],
        boolean_string_google_linkedin=boolean_strings["google_linkedin"],
        boolean_string_cake=boolean_strings["cake"],
        boolean_string_google_cake=boolean_strings["google_cake"],
        boolean_string_google_104=boolean_strings["google_104"],
        outreach_message_template=llm_output.get("outreach_message_template", ""),
        sourcing_tips=llm_output.get("sourcing_tips", []),
    )