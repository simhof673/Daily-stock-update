# pfalzinvest_daily.py
# Ziel: TÄGLICH nur den neuesten verfügbaren Schlusskurs (Datum,Kurs) ANHÄNGEN.
# Dateien: deka_pfalzinvest.csv (Append), fund_history.xlsx (für Excel-Nutzer)
# Quelle: Fondscheck "Pfalz Invest Nachhaltigkeit" (Übersichtsseite, Fondsgesellschaft-Zeile)

import os, sys, datetime as dt
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://www.fondscheck.de/pfalz_invest_nachhaltigkeit-fonds"  # Übersichtsseite
CSV = Path("deka_pfalzinvest.csv")
XLSX = Path("fund_history.xlsx")
SHEET = "Kurse"

def fetch_latest():
    """Liest die Seite und gibt (datum, kurs) des jüngsten verfügbaren Schlusskurses (Fondsgesellschaft) zurück."""
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # 1) Zeile finden, die "Fondsgesellschaft" enthält (unter 'Kurs (Fondsgesellschaft)')
    fg_row = None
    for tr in soup.find_all("tr"):
        text = tr.get_text(separator=" ", strip=True).lower()
        if "fondsgesellschaft" in text:
            tds = tr.find_all(["td","th"])
            # Erwartete Struktur: [Handelsplatz, Letzter, Vortag, Veränderung, Zeit]
            if len(tds) >= 5:
                fg_row = [td.get_text(strip=True) for td in tds]
                break

    if not fg_row:
        # Fallback: Versuche die "Letzter/Vortag"-Zeile darüber (ohne Datum) + irgendeine Datumsangabe im Umfeld
        # (robust, falls sich das Markup ändert)
        # Suche zuerst einen offensichtlichen Preis wie "52,09 €"
        price_candidate = None
        for el in soup.find_all(text=True):
            s = (el or "").strip()
            # Euroformat mit Komma und optionalem Tausenderpunkt
            if s.endswith("€") and any(ch.isdigit() for ch in s):
                price_candidate = s
                break
        # Datum irgendwo als dd.mm.yy oder dd.mm.yyyy
        date_candidate = None
        for el in soup.find_all(text=True):
            s = (el or "").strip()
            if any(c.isdigit() for c in s) and "." in s:
                for fmt in ("%d.%m.%Y", "%d.%m.%y"):
                    try:
                        dt.datetime.strptime(s, fmt)
                        date_candidate = s
                        break
                    except Exception:
                        pass
                if date_candidate:
                    break
        if price_candidate and date_candidate:
            fg_row = ["", price_candidate, "", "", date_candidate]

    if not fg_row:
        raise RuntimeError("Konnte die 'Fondsgesellschaft'-Zeile nicht finden.")

    # 2) Preis (Spalte 'Letzter') und Datum (Spalte 'Zeit') extrahieren
    letzter_str = fg_row[1]
    datum_str   = fg_row[-1]

    def parse_price(s):
        s = s.replace("€", "").replace("EUR", "").replace("\xa0"," ")
        s = s.replace(".", "").replace(" ", "").replace(",", ".")
        try:
            return float(s)
        except Exception:
            return None

    def parse_date(s):
        s = s.strip()
        for fmt in ("%d.%m.%Y", "%d.%m.%y"):
            try:
                return dt.datetime.strptime(s, fmt).date()
            except ValueError:
                pass
        # Fallback: pandas
        d = pd.to_datetime(s, dayfirst=True, errors="coerce")
        return None if pd.isna(d) else d.date()

    price = parse_price(letzter_str)
    date  = parse_date(datum_str)

    if price is None or date is None:
        raise RuntimeError(f"Ungültige Werte geparst: Preis='{letzter_str}', Datum='{datum_str}'.")

    return date, float(price)

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
