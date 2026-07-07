"""
scripts/prepare_data.py

Module C 薪資資料 ETL 腳本。
將 data_raw/ 底下的原始 Excel 整理成 app/data/ 底下的 CSV，供 service 層查詢。

執行方式（在專案根目錄下）：
    python scripts/prepare_data.py

輸入（data_raw/）：
    - 勞動部職類別薪資調查.xlsx        → 114年職類別月薪、年薪
    - 表1_各業受僱員工全年總薪資統計_按性別及教育程度分.xlsx  → 113年產業×學歷年薪中位數
    - 表3_各業受僱員工全年總薪資統計_按員工規模別分.xlsx      → 113年產業×規模年薪中位數

輸出（app/data/）：
    - mol_occupation.csv       職類碼、職類名稱、月薪、年薪
    - dgbas_education.csv      產業、學歷、年薪中位數（萬元）
    - dgbas_company_size.csv   產業、公司規模、年薪中位數（萬元）

資料來源說明：
    - 勞動部職類別薪資調查：https://pswst.mol.gov.tw/psdn/
    - 主計總處薪資統計：https://www.stat.gov.tw/News_Content.aspx?n=4580&s=232642
"""

import re
from pathlib import Path

import pandas as pd


# ── 路徑設定 ──────────────────────────────────────────────
# Path(__file__) 是這個腳本自己的路徑（scripts/prepare_data.py）
# .parent 往上一層 = scripts/
# .parent.parent 再往上一層 = 專案根目錄
ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data_raw"
OUT_DIR = ROOT / "app" / "data"

# 確保輸出資料夾存在，不存在就建立
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── 第一份：勞動部職類別薪資調查 ──────────────────────────
def prepare_mol_occupation() -> None:
    """
    整理勞動部職類別薪資調查，輸出 mol_occupation.csv。

    原始結構：
        - 第 0-2 行：標題（跳過）
        - 第 0 欄：職類名稱（含職類碼，格式為 "(242200)人力資源管理師"）
        - 第 1 欄：工業及服務業 7月經常性薪資（月薪，單位：元）
        - 第 2 欄：工業及服務業 去年全年薪資所得（年薪，單位：萬元）

    清洗步驟：
        1. 從職類名稱拆出職類碼和名稱
        2. 把無效值（--- 和 -）換成 NaN
        3. 月薪移除逗號後轉數字
        4. 過濾沒有職類碼的空行
        5. 移除七個大類父類別（100000/200000/300000/400000/500000/700000/900000）
    """
    src = RAW_DIR / "勞動部職類別薪資調查.xlsx"
    print(f"[1/3] 讀取 {src.name} ...")

    df_raw = pd.read_excel(src, header=None)

    # 只取需要的行列：從第 3 行開始，只要前三欄
    df = df_raw.iloc[3:, [0, 1, 2]].copy()
    df.columns = ["occupation_raw", "monthly_salary", "annual_salary_wan"]
    df = df.reset_index(drop=True)

    # 從職類名稱拆出職類碼和名稱
    def parse_occupation(raw: str) -> tuple[str | None, str | None]:
        raw = str(raw).strip()
        match = re.match(r'\((\d+)\)(.+)', raw)
        if match:
            return match.group(1), match.group(2).strip()
        return None, None

    df[["occupation_code", "occupation_name"]] = df["occupation_raw"].apply(
        lambda x: pd.Series(parse_occupation(x))
    )

    # 無效值換成 NaN
    df["monthly_salary"] = df["monthly_salary"].replace(["---", "-"], pd.NA)
    df["annual_salary_wan"] = df["annual_salary_wan"].replace(["---", "-"], pd.NA)

    # 月薪移除逗號後轉數字；年薪直接轉數字
    df["monthly_salary"] = (
        df["monthly_salary"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )
    df["annual_salary_wan"] = pd.to_numeric(df["annual_salary_wan"], errors="coerce")

    # 過濾沒有職類碼的行（空行或標題殘留）
    df = df[df["occupation_code"].notna()].copy()

    # 移除七個大類父類別（為子職類的彙總平均，非真實職缺）
    parent_codes = {"100000", "200000", "300000", "400000", "500000", "700000", "900000"}
    df = df[~df["occupation_code"].isin(parent_codes)].copy()

    # 整理欄位順序
    df = df[["occupation_code", "occupation_name", "monthly_salary", "annual_salary_wan"]]

    out = OUT_DIR / "mol_occupation.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"    → {out.relative_to(ROOT)} 已儲存（{len(df)} 筆，"
          f"有月薪資料 {df['monthly_salary'].notna().sum()} 筆）")


# ── 第二份：主計總處表1 學歷別 ───────────────────────────
def prepare_dgbas_education() -> None:
    """
    整理主計總處表1，輸出 dgbas_education.csv。

    原始結構（取 113 年 sheet）：
        - 前 5 行：標題（跳過）
        - 第 0 欄：產業名稱
        - 欄 8：中位數 / 全體（學歷不限）
        - 欄 11：中位數 / 國中及以下
        - 欄 12：中位數 / 高中職
        - 欄 13：中位數 / 專科及大學
        - 欄 14：中位數 / 研究所

    清洗步驟：
        1. 只取中位數欄（不取平均數、不取男女分開）
        2. 過濾空行
        3. 寬表轉長表（每個產業×學歷組合各佔一行）

    education 欄的值對應 Module D 的 EducationLevel：
        不限 → "不限"
        國中及以下、高中職 → 補充參考（不直接對應）
        專科及大學 → "大學"
        研究所 → "碩士" / "博士"
    """
    src = RAW_DIR / "表1-各業受僱員工全年總薪資統計－按性別及教育程度分.xlsx"
    print(f"[2/3] 讀取 {src.name} ...")

    df_raw = pd.read_excel(src, header=None, sheet_name="表1(113年)")

    # 只取產業名稱欄和中位數各學歷欄
    df = df_raw.iloc[5:, [0, 8, 11, 12, 13, 14]].copy()
    df.columns = ["industry", "不限", "國中及以下", "高中職", "專科及大學", "研究所"]
    df = df.reset_index(drop=True)

    # 過濾空行
    df["industry"] = df["industry"].astype(str).str.strip()
    df = df[~df["industry"].isin(["nan", ""])].copy()

    # 轉數字
    for col in ["不限", "國中及以下", "高中職", "專科及大學", "研究所"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 寬表 → 長表
    df_long = df.melt(
        id_vars=["industry"],
        value_vars=["不限", "國中及以下", "高中職", "專科及大學", "研究所"],
        var_name="education",
        value_name="median_annual_wan"
    )
    df_long = df_long.sort_values(["industry", "education"]).reset_index(drop=True)

    out = OUT_DIR / "dgbas_education.csv"
    df_long.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"    → {out.relative_to(ROOT)} 已儲存（{len(df_long)} 筆，"
          f"{df_long['industry'].nunique()} 個產業）")


# ── 第三份：主計總處表3 規模別 ───────────────────────────
def prepare_dgbas_company_size() -> None:
    """
    整理主計總處表3，輸出 dgbas_company_size.csv。

    原始結構（取 113 年 sheet）：
        - 前 5 行：標題（跳過）
        - 第 0 欄：產業名稱
        - 欄 9：中位數 / 5-99人   → 對應 company_type="startup"
        - 欄 10：中位數 / 100-299人 → 對應 company_type="SME"
        - 欄 12：中位數 / 500人以上  → 對應 company_type="enterprise"

    company_size 欄的值對應 Module A 的 company_type：
        startup    → 5-99人規模
        SME        → 100-299人規模
        enterprise → 500人以上規模
    """
    src = RAW_DIR / "表3-各業受僱員工全年總薪資統計－按員工規模別分.xlsx"
    print(f"[3/3] 讀取 {src.name} ...")

    df_raw = pd.read_excel(src, header=None, sheet_name="表3(113年)")

    # 只取產業名稱欄和對應三個規模的中位數欄
    df = df_raw.iloc[5:, [0, 9, 10, 12]].copy()
    df.columns = ["industry", "startup", "SME", "enterprise"]
    df = df.reset_index(drop=True)

    # 過濾空行
    df["industry"] = df["industry"].astype(str).str.strip()
    df = df[~df["industry"].isin(["nan", ""])].copy()

    # 轉數字
    for col in ["startup", "SME", "enterprise"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 寬表 → 長表
    df_long = df.melt(
        id_vars=["industry"],
        value_vars=["startup", "SME", "enterprise"],
        var_name="company_size",
        value_name="median_annual_wan"
    )
    df_long = df_long.sort_values(["industry", "company_size"]).reset_index(drop=True)

    out = OUT_DIR / "dgbas_company_size.csv"
    df_long.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"    → {out.relative_to(ROOT)} 已儲存（{len(df_long)} 筆，"
          f"{df_long['industry'].nunique()} 個產業）")


# ── 主程式 ────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Module C 資料準備 ===\n")
    prepare_mol_occupation()
    prepare_dgbas_education()
    prepare_dgbas_company_size()
    print("\n完成。請確認 app/data/ 底下的三份 CSV。")