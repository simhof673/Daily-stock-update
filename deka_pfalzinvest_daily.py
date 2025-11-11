# pfalzinvest_daily.py
# Ziel: TÄGLICH nur den neuesten verfügbaren Schlusskurs (Datum,Kurs) ANHÄNGEN.
# Dateien: fund_history.csv (Append), fund_history.xlsx (für Excel-Nutzer)
# Quelle: Fondscheck "Historische Kurse (Fondsgesellschaft)" (DE000A2PR6U0)

import os, sys, datetime as dt
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://www.fondscheck.de/pfalz_invest_nachhaltigkeit-fonds-historisch?boerse_id=208"  # Fondsgesellschaft
CSV = Path("deka_pfalzinvest.csv")
XLSX = Path("fund_history.xlsx")
SHEET = "Kurse"

def fetch_latest():
    """Liest die Seite und gibt (datum, kurs) des jüngsten verfügbaren Schlusskurses zurück."""
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # Tabelle mit "Datum" und "Kurs"/"Schluss" finden
    tables = soup.find_all("table")
    cand = None
    for t in tables:
        heads = [th.get_text(strip=True).lower() for th in t.find_all("th")]
        header_text = "|".join(heads)
        if "datum" in header_text and ("kurs" in header_text or "schluss" in header_text):
            cand = t
            break
    if cand is None and tables:
        cand = tables[0]
    if cand is None:
        raise RuntimeError("Keine Tabelle gefunden.")

    rows = []
    for tr in cand.find_all("tr"):
        cells = [c.get_text(strip=True) for c in tr.find_all(["td","th"])]
        if len(cells) >= 2 and cells[0].strip().lower() != "datum":
            # Fondscheck hat die Spalte 'Schluss' – wir nehmen die zweite Zelle
            rows.append(cells[:2])  # Datum, Kurs/Schluss

    if not rows:
        raise RuntimeError("Keine Kurszeilen gefunden.")

    def parse_date(s):
        s = s.strip()
        for fmt in ("%d.%m.%Y", "%d.%m.%y"):
            try:
                return dt.datetime.strptime(s, fmt).date()
            except ValueError:
                pass
        # Fallback
        return pd.to_datetime(s, dayfirst=True, errors="coerce").date()

    def parse_price(s):
        s = s.replace("€","").replace("EUR","").replace("\xa0"," ")
        s = s.replace(".","").replace(" ","").replace(",",".")
        try:
            return float(s)
        except:
            return None

    df = pd.DataFrame(rows, columns=["Datum","Kurs"])
    df["Datum"] = df["Datum"].apply(parse_date)
    df["Kurs"]  = df["Kurs"].apply(parse_price)
    df = df.dropna(subset=["Datum","Kurs"]).sort_values("Datum")
    if df.empty:
        raise RuntimeError("Parser ergab keine validen Werte.")

    latest = df.iloc[-1]
    return latest["Datum"], float(latest["Kurs"])

def load_last_csv_date():
    """Liest das jüngste Datum aus der CSV (falls vorhanden)."""
    if not CSV.exists():
        return None
    try:
        d = pd.read_csv(CSV)
        if d.empty or "Datum" not in d.columns:
            return None
        d["Datum"] = pd.to_datetime(d["Datum"]).dt.date
        return d["Datum"].max()
    except Exception:
        return None

def append_csv(row_date, row_price):
    """Hängt eine Zeile (Datum,Kurs) an CSV an – ohne Doppelte."""
    exists = False
    if CSV.exists():
        try:
            d = pd.read_csv(CSV)
            if not d.empty:
                d["Datum"] = pd.to_datetime(d["Datum"]).dt.date
                exists = (d["Datum"] == row_date).any()
        except Exception:
            pass
    if exists:
        print(f"Kein Append: {row_date} existiert bereits.")
        return False

    header_needed = not CSV.exists() or os.path.getsize(CSV) == 0
    with open(CSV, "a", encoding="utf-8", newline="") as f:
        if header_needed:
            f.write("Datum,Kurs\n")
            f.write("Datum;Kurs\n")  # (absichtlicher Doppel-Header wie im Originalskript)
        f.write(f"{row_date.isoformat()},{row_price}\n")
    print(f"Append OK: {row_date} -> {row_price}")
    return True

def sync_xlsx():
    """Optionale XLSX-Aktualisierung (aus der CSV geschrieben)."""
    if not CSV.exists():
        return
    d = pd.read_csv(CSV)
    if d.empty:
        return
    with pd.ExcelWriter(XLSX, engine="openpyxl") as w:
        d.to_excel(w, sheet_name=SHEET, index=False)

def main():
    latest_date, latest_price = fetch_latest()
    last_csv_date = load_last_csv_date()

    # Nur ANHÄNGEN, wenn neuer als der letzte CSV-Stand
    if last_csv_date is None or latest_date > last_csv_date:
        appended = append_csv(latest_date, latest_price)
        if appended:
            sync_xlsx()
            print(f"FERTIG: Neuester Eintrag {latest_date} ({latest_price}) angehängt.")
        else:
            print("Nichts zu tun (bereits vorhanden).")
    else:
        print(f"Nichts zu tun: CSV hat bereits {last_csv_date} (>= Web {latest_date}).")

if __name__ == "__main__":
    main()

