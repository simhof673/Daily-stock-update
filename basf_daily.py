# basf_daily.py
# Ziel: TÄGLICH nur den neuesten verfügbaren Schlusskurs (Datum,Kurs) ANHÄNGEN.
# Datei: BASF.csv
# Quelle: Stooq-Tagesdaten BAS.DE

import os
import datetime as dt
from pathlib import Path
import io

import pandas as pd
import requests

# Stooq: tägliche Kurse für BASF (XETRA), Symbol BAS.DE
URL = "https://stooq.com/q/d/l/?s=bas.de&i=d"
CSV = Path("basf.csv")


def fetch_latest():
    """
    Lädt das Stooq-CSV für BAS.DE und gibt (datum, kurs) des jüngsten
    verfügbaren Schlusskurses zurück.
    """
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()

    text = r.text.strip()
    if not text:
        raise RuntimeError("Leere Antwort von Stooq.")

    # Stooq-Format: Date,Open,High,Low,Close,Volume
    df = pd.read_csv(io.StringIO(text))

    if "Date" not in df.columns or "Close" not in df.columns:
        raise RuntimeError(f"Unerwartete Spalten im CSV: {df.columns.tolist()}")

    # Date in echtes Datum konvertieren
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    df = df.dropna(subset=["Date", "Close"])
    df = df.sort_values("Date")

    if df.empty:
        raise RuntimeError("Keine validen Kursdaten gefunden.")

    latest = df.iloc[-1]
    latest_date = latest["Date"]
    latest_close = float(latest["Close"])

    return latest_date, latest_close


def load_last_csv_date():
    """
    Liest das jüngste Datum aus BASF.csv (falls vorhanden).
    Erwartet Spalte 'Datum'.
    """
    if not CSV.exists():
        return None

    try:
        d = pd.read_csv(CSV)
    except Exception:
        # Wenn Datei kaputt ist, lieber nichts tun
        return None

    if d.empty or "Datum" not in d.columns:
        return None

    d["Datum"] = pd.to_datetime(d["Datum"], errors="coerce").dt.date
    d = d.dropna(subset=["Datum"])

    if d.empty:
        return None

    return d["Datum"].max()


def append_csv(row_date: dt.date, row_price: float):
    """
    Hängt eine Zeile (Datum,Kurs) an BASF.csv an – ohne Doppelte.
    Spalten: Datum,Kurs
    """
    exists = False
    if CSV.exists():
        try:
            d = pd.read_csv(CSV)
            if not d.empty and "Datum" in d.columns:
                d["Datum"] = pd.to_datetime(d["Datum"], errors="coerce").dt.date
                exists = (d["Datum"] == row_date).any()
        except Exception:
            # Wenn Lesen fehlschlägt, versuchen wir trotzdem anzuhängen.
            pass

    if exists:
        print(f"Kein Append: {row_date} existiert bereits in BASF.csv.")
        return False

    header_needed = not CSV.exists() or os.path.getsize(CSV) == 0

    with open(CSV, "a", encoding="utf-8", newline="") as f:
        if header_needed:
            f.write("Datum,Kurs\n")
        # Punkt als Dezimaltrenner, 4 Nachkommastellen
        f.write(f"{row_date.isoformat()},{row_price:.4f}\n")

    print(f"Append OK: {row_date} -> {row_price:.4f}")
    return True


def main():
    latest_date, latest_price = fetch_latest()
    print(f"Web: Neuester BASF-Schlusskurs {latest_date} = {latest_price:.4f}")

    last_csv_date = load_last_csv_date()
    if last_csv_date is None:
        print("BASF.csv: keine/keine gültigen Einträge gefunden.")
    else:
        print(f"BASF.csv: letzter Eintrag = {last_csv_date}")

    # Nur anhängen, wenn das Web-Datum neuer ist
    if last_csv_date is None or latest_date > last_csv_date:
        appended = append_csv(latest_date, latest_price)
        if appended:
            print(
                f"FERTIG: Neuester Eintrag {latest_date} "
                f"({latest_price:.4f}) in BASF.csv angehängt."
            )
        else:
            print("Nichts zu tun (Datum bereits vorhanden).")
    else:
        print(
            f"Nichts zu tun: CSV hat bereits {last_csv_date} (>= Web {latest_date})."
        )


if __name__ == "__main__":
    main()
