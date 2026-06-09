# PrinterLogic Output Demo

A suite of tools for demo-ing Vasion Output with realistic, industry-specific print traffic. Use any combination simultaneously — they all share a single `settings.json` so you configure credentials once.

## What's Included

| App | Port | Description |
|-----|------|-------------|
| 🖨️ **Print Job Seeder** | 5757 | Bulk print-job generator with industry presets |
| 🏭 **Apex Industrial ERP Demo** | 5758 | Fake manufacturing ERP with orders, customers, and print workflows |
| 🏥 **Meridian Health EMR Demo** | 5759 | Fake healthcare EMR with patients, encounters, and clinical document printing |
| 🖧 **Virtual Printer (JetDirect)** | 9100 | TCP listener that accepts and acknowledges raw print jobs on port 9100 |

---

## Option 1 — Standalone Executable (Recommended)

No Python installation required. A single `.exe` (Windows) or `.app` (Mac) bundles everything.

### Running on Windows

1. Double-click **`PrinterLogicOutputDemo.exe`**
2. A launcher window appears with checkboxes for each app
3. Tick the apps you want, then click **Launch**
4. Each selected app opens in your default browser automatically
5. Keep the launcher window open while the apps are in use — closing it stops everything

To expose server logs, run from a terminal with the `--console` flag:
```
PrinterLogicOutputDemo.exe --console
```

### Running on Mac

1. Double-click **`PrinterLogicOutputDemo.app`** (or `PrinterLogicOutputDemo` binary)
2. A browser tab opens at **http://localhost:5750** — the launcher control panel
3. Tick the apps you want, then click **Launch**
4. Each selected app opens in a new browser tab automatically
5. Keep the launcher tab open while the apps are in use — clicking **Quit** stops everything

> **Gatekeeper prompt:** On first launch macOS may warn the app is from an unidentified developer. Right-click the app → **Open** → **Open** to allow it.

---

## Option 2 — Build the Executable Yourself

If you have Python installed and want to produce the `.exe` or `.app` from source:

### Windows — build the `.exe`

```bat
Build-Exe.bat
```

This creates a virtual environment, installs all dependencies including PyInstaller, and produces `dist\PrinterLogicOutputDemo.exe`. The resulting file is self-contained — copy it to any Windows machine and run it without Python.

### Mac — build the `.app`

```bash
chmod +x Build-App.sh
./Build-App.sh
```

This does the same for macOS, producing `dist/PrinterLogicOutputDemo.app`. Copy the `.app` bundle to any Mac and double-click to run.

> Both build scripts use the corresponding PyInstaller spec file (`PrinterLogicOutputDemo.spec` / `PrinterLogicOutputDemo-Mac.spec`).

---

## Option 3 — Run from Source (Scripts / Terminal)

If you prefer to run directly from Python without building an executable, use the start/stop scripts or run the apps manually.

### Windows Scripts

| Script | Purpose |
|--------|---------|
| `Start-PrintJobSeeder.bat` | Start Print Job Seeder on port 5757 |
| `Stop-PrintJobSeeder.bat` | Stop the Print Job Seeder |
| `Start-ERPDemo.bat` | Start the Apex Industrial ERP Demo on port 5758 |
| `Stop-ERPDemo.bat` | Stop the ERP Demo |

Scripts create a virtual environment and install dependencies automatically on first run.

**To start the Print Job Seeder:**
```bat
Start-PrintJobSeeder.bat
```

**To start the ERP Demo:**
```bat
Start-ERPDemo.bat
```

### Mac / Linux Scripts

Make the scripts executable once after cloning:
```bash
chmod +x Start-PrintJobSeeder.command Start-ERPDemo.command
chmod +x Start-PrintJobSeeder.sh Stop-PrintJobSeeder.sh
chmod +x Start-ERPDemo.sh Stop-ERPDemo.sh
```

**Double-click launchers (Mac Finder):** `Start-PrintJobSeeder.command`, `Start-ERPDemo.command`

**From the terminal:**
```bash
./Start-PrintJobSeeder.sh    # port 5757
./Start-ERPDemo.sh           # port 5758
```

Shell scripts run in the background via `nohup`, writing logs to `printjobseeder.log` / `erp_demo.log` and saving a `.pid` file for clean shutdown via the corresponding stop script.

To stop:
```bash
./Stop-PrintJobSeeder.sh
./Stop-ERPDemo.sh
```

### Manual Setup (any platform)

```bash
# Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run individual apps
python app.py          # Print Job Seeder  — http://localhost:5757
python app_erp.py      # ERP Demo          — http://localhost:5758
python app_emr.py      # EMR Demo          — http://localhost:5759

# Or run the full launcher (Tkinter on Windows, browser on Mac)
python launcher.py
```

> **Requirements:** Python 3.8 or higher

---

## Initial Configuration

All apps share a single `settings.json` — configure credentials once and every app uses them.

Open Settings via the **gear icon** in the Print Job Seeder, or the **Admin** page in the ERP / EMR Demo.

### API Destinations

**Cloud Link** — Vasion's cloud-hosted Output service:

| Region | Domain |
|--------|--------|
| US | printercloud.com |
| EMEA | printercloud5.com |
| ASIAPAC | printercloud10.com |
| Canada | printercloud15.com |
| SE-ASIAPAC | printercloud20.com |
| US-NOW | printercloudnow.com |

**On-Premise** — Self-hosted Output server. Configure server address, protocol (HTTP/HTTPS), port (default 443 / 31990), and bearer token.

> 💡 Get your API key from the Vasion Admin Console: **Tools > Tokens > API Keys**

### Industry Printer Path Filters

Each industry uses a wildcard to query printers from the Vasion API by folder path:

| Industry | Default filter |
|----------|---------------|
| Healthcare | `*Healthcare*` |
| Manufacturing | `*Manufacturing*` |
| Legal | `*Legal*` |
| Finance | `*Finance*` |
| Education | `*Education*` |

---

## The Apps in Detail

### 🖨️ Print Job Seeder (port 5757)

- **Multi-industry** — Healthcare, Manufacturing, Legal, Finance, Education
- **Automate All mode** — fetches printers from Vasion and applies presets in one click
- **On-the-fly PDF generation** — variable page counts with industry-appropriate content
- **Flexible timing** — fixed delays or randomized "natural" timing
- **Real-time progress** with stop support and session persistence

### 🏭 Apex Industrial ERP Demo (port 5758)

- **Dashboard** — KPI cards and Chart.js charts for work orders and print volume
- **Orders** — 30 Work Orders and 20 Purchase Orders; print individual rows or bulk-select with SSE progress
- **Customers** — 15 fake manufacturing companies with contacts
- **Print Queue** — Single-job quick-send and background bulk run with live log
- **Admin** — Settings page writing to the shared `settings.json`

Fake data is generated at startup with a fixed seed for stable, consistent demos.

### 🏥 Meridian Health EMR Demo (port 5759)

- **Dashboard** — KPI cards (Active Patients, Open Encounters, Avg Wait, Documents Printed) and Chart.js charts
- **Patients** — 20 fake patients with MRN, provider, insurer; print records per patient
- **Encounters & Orders** — 30 Encounters and 24 Lab/Imaging Orders; print clinical notes and requisitions individually or in bulk with SSE progress
- **Print Queue** — Single clinical document quick-send and background bulk run; always uses the Healthcare printer folder
- **Admin** — Same shared settings page

All print jobs from the EMR Demo use `healthcare` industry documents (discharge summaries, lab results, prescriptions, radiology reports, etc.) and `@meridianhealth.org`-style usernames.

### 🖧 Virtual Printer (port 9100)

A lightweight TCP server that accepts raw JetDirect/AppSocket connections on port 9100. It receives the print data, discards the bytes, and closes the connection cleanly — which is the success signal for the raw port 9100 protocol. Vasion marks the job as successfully printed.

Started from the launcher only (no separate script). Once running, configure a printer in your Vasion instance with:
- **IP address:** `127.0.0.1`
- **Port:** `9100`
- **Protocol:** Raw / JetDirect / AppSocket

The launcher status panel shows a live connection log (one line per completed job).

---

## Industry Presets

Each industry includes **40 realistic filenames** and **20 username presets**.

| Industry | Sample filenames | Sample domains |
|----------|-----------------|----------------|
| 🏥 Healthcare | `Lab_Results_RWilliams_1847.pdf`, `Surgical_Consent_DMartin.pdf`, `MRI_Results_TKing_Brain.pdf` | `@mercyvalleymed.org`, `@stlukeshealth.net` |
| 🏭 Manufacturing | `Work_Order_WO78542.pdf`, `Quality_Inspection_QI2024_0892.pdf`, `Bill_of_Materials_BOM_A4521.pdf` | `@apexindustrial.com` |
| ⚖️ Legal | `Contract_Agreement_Smith_v_Jones.pdf`, `Deposition_Transcript_RWilliams.pdf`, `Motion_to_Dismiss_MTD_Filed.pdf` | `@sterlinglaw.com`, `@hamiltonlegal.net` |
| 💰 Finance | `Quarterly_Report_Q3_2024.pdf`, `Invoice_INV_2024_08547.pdf`, `Portfolio_Analysis_PA_Equity.pdf` | `@oakgrovebank.com`, `@firsttrustfinancial.net` |
| 🎓 Education | `Student_Transcript_ST_JSmith.pdf`, `Course_Syllabus_CS_Math101.pdf`, `Financial_Aid_FA_App_2025.pdf` | `@oakwoodacademy.edu`, `@lincolnschools.org` |

---

## Timing Modes

### Fixed Delay
Consistent delay between jobs. Good for predictable, controlled testing.

### Random Timing
Randomized delays that simulate real user behavior:
- **50%** — Quick succession (0.5–3 s), simulating batch printing
- **30%** — Moderate gaps (3–30 s), normal work rhythm
- **20%** — Longer pauses (30 s+), coffee breaks and meetings

---

## Debugging & Logging

Both apps write detailed request/response logs to `request_log.txt`.

**Watch live on Windows (PowerShell):**
```powershell
Get-Content "request_log.txt" -Wait -Tail 50
```

**Watch live on Mac/Linux:**
```bash
tail -f request_log.txt
```

---

## API Reference

### Send a Print Job
```
POST {base_url}/v1/jobs
Authorization: Bearer {api_key_or_token}
Content-Type: multipart/form-data

file:     {PDF file}
title:    {printer name}
copies:   "1"
username: {username}
```

### Fetch Printers
```
GET {base_url}/v1/printers?path={folder_path}&fields=id,title&limit=100
Authorization: Bearer {api_key}
```

The `path` parameter supports wildcards (e.g., `*Healthcare*`) to filter by folder.

---

## File Structure

| File | Purpose |
|------|---------|
| `launcher.py` | Unified entry point — Tkinter on Windows, browser UI on Mac |
| `app.py` | Print Job Seeder (port 5757) |
| `app_erp.py` | Apex Industrial ERP Demo (port 5758) |
| `app_emr.py` | Meridian Health EMR Demo (port 5759) |
| `virtual_printer.py` | JetDirect TCP listener (port 9100) |
| `print_utils.py` | Shared constants, settings, PDF generation, job sending |
| `settings.json` | Shared credentials and configuration (all apps read/write here) |
| `templates/erp/` | ERP Demo HTML templates |
| `templates/emr/` | EMR Demo HTML templates |
| `templates/index.html` | Print Job Seeder UI |
| `PrinterLogicOutputDemo.spec` | PyInstaller spec for Windows `.exe` |
| `PrinterLogicOutputDemo-Mac.spec` | PyInstaller spec for Mac `.app` |
| `Build-Exe.bat` | Windows build script |
| `Build-App.sh` | Mac build script |


