# deka_globalchampions_daily.py
# Fetch daily "Schlusskurse" for Deka-GlobalChampions (ISIN DE000DK0ECU8)
# Writes/updates fund_history.xlsx and fund_history.csv in repo root.
import os, sys, datetime as dt
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://de.marketscreener.com/kurs/fond/DEKA-GLOBALCHAMPIONS-52081469/"
OUT_XLSX = Path("fund_history.xlsx")
OUT_CSV = Path("fund_history.csv")
SHEET = "Kurse"

def fetch_table():
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(URL, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    tables = soup.find_all("table")
    candidates = []
    for t in tables:
        headers = [th.get_text(strip=True) for th in t.find_all("th")]
        header_text = "|".join(headers).lower()
        if ("datum" in header_text) and ("kurs" in header_text or "schluss" in header_text):
            candidates.append(t)
    if not candidates and tables:
        candidates = [tables[0]]
    rows = []
    if candidates:
        for tr in candidates[0].find_all("tr"):
            cells = [c.get_text(strip=True) for c in tr.find_all(["td","th"])]
            if len(cells) >= 2 and cells[0].lower() != "datum":
                rows.append(cells[:3])
    df = pd.DataFrame(rows, columns=["Datum","Kurs","_pct"] if rows and len(rows[0])==3 else ["Datum","Kurs"])
    if df.empty:
        return df
    def parse_date(s):
        for fmt in ("%d.%m.%Y","%d.%m.%y"):
            try:
                return dt.datetime.strptime(s.strip(), fmt).date()
            except ValueError:
                pass
        return pd.to_datetime(s, dayfirst=True, errors="coerce").date()
    def parse_price(s):
        s = s.replace("€","").replace("EUR","").replace("\xa0"," ")
        s = s.replace(".","").replace(" ","").replace(",",".")
        try:
            return float(s)
        except:
            return pd.NA
    df["Datum"] = df["Datum"].apply(parse_date)
    df["Kurs"] = df["Kurs"].apply(parse_price)
    df = df.dropna(subset=["Datum","Kurs"]).astype({"Kurs":"float"})
    df = df[["Datum","Kurs"]].drop_duplicates().sort_values("Datum")
    return df

def load_existing():
    if OUT_XLSX.exists():
        try:
            ex = pd.read_excel(OUT_XLSX, sheet_name="Kurse", engine="openpyxl")
            ex["Datum"] = pd.to_datetime(ex["Datum"]).dt.date
            return ex[["Datum","Kurs"]].drop_duplicates().sort_values("Datum")
        except Exception:
            pass
    if OUT_CSV.exists():
        try:
            ex = pd.read_csv(OUT_CSV)
            ex["Datum"] = pd.to_datetime(ex["Datum"]).dt.date
            ex["Kurs"] = ex["Kurs"].astype(float)
            return ex[["Datum","Kurs"]].drop_duplicates().sort_values("Datum")
        except Exception:
            pass
    return pd.DataFrame(columns=["Datum","Kurs"])

def save_all(df):
    df = df.drop_duplicates().sort_values("Datum")
    # Write Excel
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Kurse", index=False)
    # Write CSV (for easy raw URL consumption via Power Query/SharePoint/etc.)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8")

def main():
    web = fetch_table()
    if web.empty:
        print("WARN: keine Web-Daten – behalte bisherigen Stand.")
        existing = load_existing()
        if existing.empty:
            sys.exit("ERROR: Keine Daten verfügbar.")
        save_all(existing)
        return
    merged = pd.concat([load_existing(), web], ignore_index=True).drop_duplicates().sort_values("Datum")
    save_all(merged)
    print(f"Aktualisiert: {len(merged)} Zeilen, letztes Datum: {merged['Datum'].max()}")

if __name__ == "__main__":
    main()
