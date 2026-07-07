"""
模組 C：Salary Competitiveness Detector — Service 層

處理流程：
  1. load_salary_data()       ：啟動時讀取三份 CSV 到記憶體
  2. extract_jd_salary()      ：規則層，從 JD 文字解析是否已提供薪資範圍
  3. build_salary_context()   ：查詢層，從 CSV 撈出對應參考數字，組成給 LLM 的背景資料
  4. check_salary()           ：主函式，整合以上，呼叫 LLM 推估薪資競爭力
"""

import os
import re
import json
import pandas as pd
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from app.models.salary_schemas import (
    SalaryCheckRequest,
    SalaryCheckResponse,
    MarketSalaryRange,
)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ── 資料路徑 ──────────────────────────────────────────────
# Path(__file__) 是這個檔案自己的路徑（app/services/salary_service.py）
# .parent.parent 往上兩層 = 專案根目錄 / app/data/
_DATA_DIR = Path(__file__).parent.parent / "data"


# ── 1. 讀取 CSV ───────────────────────────────────────────

def load_salary_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    讀取三份薪資參考 CSV，回傳給後續查詢函式使用。
    在 module 層級被呼叫一次，不在每次 API 請求時重複執行。

    回傳：
        df_occupation  : 勞動部職類別薪資（職類碼、職類名稱、月薪平均數、年薪平均數（萬元））
        df_education   : 主計總處學歷別薪資（產業、學歷、年薪中位數）
        df_company_size: 主計總處規模別薪資（產業、公司規模、年薪中位數）
    """
    df_occupation = pd.read_csv(
        _DATA_DIR / "mol_occupation.csv",
        dtype={"occupation_code": str}  # 職類碼保留字串，避免前導零被移除
    )
    df_education = pd.read_csv(_DATA_DIR / "dgbas_education.csv")
    df_company_size = pd.read_csv(_DATA_DIR / "dgbas_company_size.csv")

    return df_occupation, df_education, df_company_size


# 在 module 層級執行一次，之後所有呼叫共用同一份資料
df_occupation, df_education, df_company_size = load_salary_data()


# ── 2. 規則層：從 JD 解析薪資範圍 ────────────────────────

def extract_jd_salary(jd_text: str) -> str | None:
    """
    從 JD 文字中用正規表達式解析薪資範圍。
    有找到薪資描述 → 回傳薪資字串（例：「45,000–60,000 元」）
    找不到 → 回傳 None，讓 LLM 知道 JD 未揭露薪資

    支援的格式：
      - 45000~60000、45,000～60,000（範圍）
      - 月薪 50000、年薪 80 萬、起薪 45,000 元（單一金額）
      - 薪資面議、待遇面議、薪資再議等（面議類）
    """
    # 薪資面議：有提及但未揭露數字
    # 涵蓋常見台灣 JD 寫法：
    #   薪資面議、薪資可面議、薪資另外面議、薪資再議
    #   待遇面議、待遇優渥面議
    #   面議（單獨出現）
    if re.search(r"(薪資|待遇).{0,5}(面議|再議|另議)", jd_text) or \
       re.search(r"^面議$", jd_text.strip()):
        return "薪資面議（未揭露具體數字）"

    # 數字範圍：45000~60000 或 45,000～60,000
    range_match = re.search(
        r"(\d{1,3}(?:,\d{3})*|\d+)\s*[~～\-–—]\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(?:元|萬|k|K)?",
        jd_text
    )
    if range_match:
        return f"{range_match.group(1)}–{range_match.group(2)} 元"

    # 單一金額：月薪 50000、年薪 80 萬、起薪 45,000 元
    single_match = re.search(
        r"(?:月薪|薪資|薪水|年薪|底薪|起薪|本薪)\s*[：:]?\s*(\d{1,3}(?:,\d{3})+|\d+)\s*(元|萬|k|K)?",
        jd_text
    )
    if single_match:
        number = single_match.group(1)
        unit = single_match.group(2) or "元"
        return f"{number} {unit}"

    return None


# ── 3. 查詢層：從 CSV 撈出參考數字 ──────────────────────

def build_salary_context(
    job_title: str,
    industry: str | None,
    company_type: str | None,
    education_level: str | None,
    seniority_level: str | None,
) -> str:
    """
    從三份 CSV 查詢對應的薪資參考數字，組成給 LLM 的背景資料字串。

    查詢邏輯：
      - 勞動部職類別：列出所有職類名稱供 LLM 參考，由 LLM 自行映射最接近的職類
      - 主計總處學歷別：若有 industry + education_level，查對應中位數；否則用全體
      - 主計總處規模別：若有 industry + company_type，查對應中位數；否則用全體

    為什麼不在 Python 層做職類映射：
      職稱對應官方職類需要語意理解（例："Growth Hacker" → 廣告及行銷專業人員），
      這是 LLM 擅長的工作，Python 字串比對無法處理這類模糊映射。
    """
    lines = []

    # ── 勞動部：列出所有職類供 LLM 映射 ──────────────────
    lines.append("【勞動部職類別薪資基準｜114年｜平均數｜工業及服務業整體】")
    lines.append(f"請從以下職類中找出與「{job_title}」最接近的項目作為薪資基準：")
    for _, row in df_occupation.iterrows():
        monthly = f"{int(row['monthly_salary']):,}" if pd.notna(row["monthly_salary"]) else "無資料"
        annual = f"{row['annual_salary_wan']:.1f}" if pd.notna(row["annual_salary_wan"]) else "無資料"
        lines.append(f"  - {row['occupation_name']}（{row['occupation_code']}）：月薪 {monthly} 元 / 年薪 {annual} 萬元")

    # ── 主計總處學歷別：查詢對應產業 × 學歷 ──────────────
    lines.append("\n【主計總處學歷別薪資｜113年｜中位數｜工業及服務業整體】")

    # 學歷對應：Module D 的 EducationLevel → 主計總處的學歷分類
    edu_mapping = {
        "大學": "專科及大學",
        "碩士": "研究所",
        "博士": "研究所",  # 博士歸入研究所（主計總處無博士單獨分類）
        "不限": "不限",
    }
    edu_key = edu_mapping.get(education_level, "不限") if education_level else "不限"

    # 先嘗試查對應產業，找不到就用全體
    edu_industry = industry if industry else "全體"
    edu_row = df_education[
        (df_education["industry"] == edu_industry) &
        (df_education["education"] == edu_key)
    ]
    if edu_row.empty and edu_industry != "全體":
        # 找不到對應產業，fallback 到全體
        edu_industry = "全體"
        edu_row = df_education[
            (df_education["industry"] == "全體") &
            (df_education["education"] == edu_key)
        ]
        lines.append(f"（產業「{industry}」無法直接對應，改用全體數據）")

    if not edu_row.empty:
        val = edu_row.iloc[0]["median_annual_wan"]
        lines.append(f"  學歷（{edu_key}）× 產業（{edu_industry}）年薪中位數：{val:.1f} 萬元")
    else:
        lines.append("  學歷別薪資：無對應資料")

    # ── 主計總處規模別：查詢對應產業 × 公司規模 ──────────
    lines.append("\n【主計總處規模別薪資｜113年｜中位數｜工業及服務業整體】")

    size_industry = industry if industry else "全體"
    size_key = company_type if company_type else None

    if size_key:
        size_row = df_company_size[
            (df_company_size["industry"] == size_industry) &
            (df_company_size["company_size"] == size_key)
        ]
        if size_row.empty and size_industry != "全體":
            # 找不到對應產業，fallback 到全體
            size_industry = "全體"
            size_row = df_company_size[
                (df_company_size["industry"] == "全體") &
                (df_company_size["company_size"] == size_key)
            ]
            lines.append(f"（產業「{industry}」無法直接對應，改用全體數據）")

        if not size_row.empty:
            val = size_row.iloc[0]["median_annual_wan"]
            lines.append(f"  規模（{size_key}）× 產業（{size_industry}）年薪中位數：{val:.1f} 萬元")
        else:
            lines.append("  規模別薪資：無對應資料")
    else:
        lines.append("  公司規模未提供，略過規模別參考")

    # ── 年資層級補充說明 ──────────────────────────────────
    if seniority_level:
        seniority_hint = {
            "junior": "junior（通常對應 1–3 年經驗，薪資約落在市場 P25–P50）",
            "mid":    "mid（通常對應 3–7 年經驗，薪資約落在市場 P50–P75）",
            "senior": "senior（通常對應 7 年以上經驗，薪資約落在市場 P75 以上）",
        }
        lines.append("\n【年資層級參考】")
        lines.append(f"  {seniority_hint.get(seniority_level, seniority_level)}")

    return "\n".join(lines)


# ── 4. 主函式：整合規則層 + LLM ──────────────────────────

def check_salary(request: SalaryCheckRequest) -> SalaryCheckResponse:
    """
    Module C 的主要進入點，供 router 呼叫。

    執行順序：
      1. extract_jd_salary()    ：規則層，解析 JD 是否已揭露薪資
      2. build_salary_context() ：查詢層，從 CSV 撈出對應參考數字
      3. 呼叫 LLM               ：傳入職稱、背景資料、JD 薪資，推估競爭力
      4. 解析回傳               ：對應 SalaryCheckResponse schema
    """
    # 步驟一：規則層
    jd_salary = extract_jd_salary(request.job_description_text)

    # 步驟二：查詢層
    salary_context = build_salary_context(
        job_title=request.job_title,
        industry=request.industry,
        company_type=request.company_type,
        education_level=request.education_level,
        seniority_level=request.seniority_level,
    )

    # 步驟三：組 prompt 並呼叫 LLM
    # 優先用 HR 直接填寫的薪資欄位，其次用 JD 文字解析結果

    if request.salary_min and request.salary_max:
        jd_salary_str = f"JD 薪資範圍（HR 填寫）：{request.salary_min:,}–{request.salary_max:,} 元／月"
    elif request.salary_min:
        jd_salary_str = f"JD 薪資下限（HR 填寫）：{request.salary_min:,} 元／月"
    elif jd_salary:
        jd_salary_str = f"JD 揭露薪資（從 JD 文字解析）：{jd_salary}"
    else:
        jd_salary_str = "JD 未揭露薪資範圍"


    prompt = f"""
你是一位熟悉台灣就業市場的資深招募顧問，請根據以下資料推估這個職缺的薪資競爭力。

【輸入資訊】
職稱：{request.job_title}
產業：{request.industry or "未提供"}
公司規模：{request.company_type or "未提供"}
年資層級：{request.seniority_level or "未提供"}
學歷要求：{request.education_level or "未提供"}
{jd_salary_str}

【薪資參考資料】
{salary_context}

【推估指引】
1. 從勞動部職類清單中找出與「{request.job_title}」語意最接近的職類，作為月薪基準
2. 參考主計總處學歷別與規模別數字，判斷修正方向（上調或下調）
3. 考量年資層級對薪資的影響（junior/mid/senior）
4. 若 JD 有揭露薪資，與市場區間對比，判斷競爭力等級
5. 若 JD 未揭露薪資，根據市場數字給出建議區間，並說明「薪資未揭露」本身對吸引力的影響

【注意事項】
- 兩個資料來源統計方式不同：勞動部為平均數，主計總處為中位數，請在推估時留意
- 若職稱無法精確對應官方職類，請說明映射邏輯並調低 confidence_level
- 若產業無法對應主計總處分類，請使用「全體」數據並說明
- 若學歷要求為「博士」，參考數字來自主計總處「研究所」分類（含博士），實際薪資通常高於該中位數，請在推估時適度上調
- disclaimer 必須標註正確資料年份：勞動部職類別薪資調查為 114 年、主計總處薪資統計為 113 年

請用以下 JSON 格式回答，不要加任何其他文字或 markdown 標記：
{{
  "p25_monthly": 市場薪資 P25（整數，月薪，單位為新台幣元，例：75000 代表 75,000 元，不要填 75 或 75.0）,
  "median_monthly": 市場薪資中位數（整數，月薪，單位為新台幣元，例：98000 代表 98,000 元，不要填 98 或 98.0）,
  "p75_monthly": 市場薪資 P75（整數，月薪，單位為新台幣元，例：120000 代表 120,000 元，不要填 120 或 120.0）,
  "competitiveness_level": "高度競爭" 或 "具競爭力" 或 "普通" 或 "偏低" 或 "明顯偏低",
  "competitiveness_reason": "60-100 字的判斷理由",
  "salary_suggestion": "60-100 字的具體薪資建議",
  "data_sources": "本次推估實際引用的資料來源說明",
  "confidence_level": "high" 或 "medium" 或 "low",
  "confidence_reason": "40-60 字的可信度說明",
  "disclaimer": "資料限制與使用提醒（需包含：資料年份、統計方式差異、建議搭配即時平台驗證）"
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,  # 薪資推估需要穩定性，溫度設低
    )

    result = json.loads(response.choices[0].message.content)

    # 步驟四：解析回傳，組成 SalaryCheckResponse
    return SalaryCheckResponse(
        market_salary_range=MarketSalaryRange(
            p25_monthly=result["p25_monthly"],
            median_monthly=result["median_monthly"],
            p75_monthly=result["p75_monthly"],
        ),
        competitiveness_level=result["competitiveness_level"],
        competitiveness_reason=result["competitiveness_reason"],
        salary_suggestion=result["salary_suggestion"],
        data_sources=result["data_sources"],
        confidence_level=result["confidence_level"],
        confidence_reason=result["confidence_reason"],
        disclaimer=result["disclaimer"],
    )