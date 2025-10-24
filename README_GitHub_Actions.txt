
Cloud-Update ohne PC: GitHub Actions
====================================

Was bekomme ich?
----------------
Ein Repository-Setup, das **täglich im GitHub-Backend** läuft (auch wenn dein Rechner aus ist)
und die Dateien **fund_history.xlsx** und **fund_history.csv** aktualisiert.

Einrichtung (einmalig, ~3 Minuten)
----------------------------------
1. **Neues privates Repository** auf GitHub anlegen (z. B. `fund-DE000DK0ECU8`).
2. Die drei Dateien aus diesem Ordner in das Repo hochladen:
   - `deka_globalchampions_daily.py`
   - `.github/workflows/update_fund.yml`
   - *(optional)* eine leere `fund_history.xlsx` (wird sonst erzeugt).
3. Reiter **Actions** öffnen → den Workflow „Update DE000DK0ECU8 daily“ aktivieren.
4. Test: **Run workflow** klicken. Danach sollten `fund_history.*` vorhanden/aktualisiert sein.

Zeitplan
--------
- Im Workflow ist `cron: "30 16 * * *"` gesetzt → **16:30 UTC**.
  - In **Europa/Berlin** entspricht das ca. **18:30** im Winter (CET) bzw. **18:30** während der Sommerzeit (CEST; GitHub bleibt UTC).
- Uhrzeit ändern? In `.github/workflows/update_fund.yml` die `cron`-Zeile anpassen.

Excel/Power Query lesen (ohne PC-Update)
----------------------------------------
Option A: **CSV aus GitHub**:
- In Excel **Daten > Aus dem Web** und die **Raw-URL** zur `fund_history.csv` verwenden.
  (Im Repo auf die CSV klicken → „Raw“ → die URL kopieren.)

Option B: **SharePoint/OneDrive gespiegelt**
- Wenn ihr einen Spiegel-Job (z. B. Power Automate Cloudflow, Azure Function, o.ä.) habt,
  lasst die CSV/XLSX dorthin kopieren – Excel-Dateien in SharePoint/Teams aktualisieren sich dann per Verbindung.

Hinweise
--------
- Quelle: MarketScreener-Fondsporträt für **DE000DK0ECU8** (Schlusskurse). Prüfe ggf. Nutzungsbedingungen.
- Wenn MarketScreener die Seite umstellt, muss der Parser (Spalten „Datum“/„Kurs“) angepasst werden.
- Für **NAV direkt von der KVG** kann das Skript auf eine andere Quelle zeigen.

Sicherheit
---------
- Das Repo kann **privat** bleiben. Power Query kann auch aus privaten Repos lesen, wenn ihr einen
  Gateway/Token-Ansatz nutzt – einfacher ist i. d. R. ein **öffentliches** CSV-Only Repo oder ein Artefakt-Spiegel nach SharePoint.
