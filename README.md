# Print Job Seeder

Two tools for demo-ing Vasion Output with realistic, industry-specific print traffic — use either independently or together.

## What's Included

### 🖨️ Print Job Seeder

A browser-based utility for sending bulk print jobs to Vasion Output's API. Choose one or more industries, configure printers and filenames, and populate the Output Console with realistic-looking jobs — great for demos and testing.

- **Multi-industry support** — Healthcare, Manufacturing, Legal, Finance, Education
- **Automate All mode** — fetches printers from Vasion and applies presets in one click
- **On-the-fly PDF generation** — variable page counts with industry-appropriate content
- **Flexible timing** — fixed delays or randomized "natural" timing that mimics real users
- **Real-time progress** with stop support and session persistence (reconnects if you close the tab)

Runs at **http://localhost:5757**

### 🏭 Apex Industrial ERP Demo

A polished, customer-facing fake manufacturing ERP system that wraps the same print engine. Designed for sales demos where showing Vasion Output integrated into an enterprise workflow is more compelling than a standalone tool.

- **Professional ERP interface** — fixed sidebar, navy color scheme, KPI dashboard with live charts
- **Fake manufacturing data** — 30 Work Orders, 20 Purchase Orders, 15 Customers
- **Live print flow** — print individual orders or bulk-print selections with real-time SSE progress
- **Shared settings** — credentials configured in one app are available in the other

Runs at **http://localhost:5758**

> 💡 Both apps can run simultaneously — they use separate ports and share the same `settings.json`.

---

## Quick Start — Windows

Both apps manage their own Python virtual environment on first run — no manual setup needed.

### Print Job Seeder

1. Double-click **`Start-PrintJobSeeder.bat`**
   - Creates a venv and installs dependencies on first run
   - Starts the server on port 5757 and opens **http://localhost:5757** in your browser
2. Click the **gear icon** to open Settings and enter your API credentials
3. Select your API destination, pick industries, and click **Send Print Jobs**

To stop: double-click **`Stop-PrintJobSeeder.bat`**

### ERP Demo

1. Double-click **`Start-ERPDemo.bat`**
   - Starts the server on port 5758 and opens **http://localhost:5758** in your browser
2. Click **Admin** in the left sidebar to configure API credentials
3. Use the **Orders** or **Print Queue** pages to send jobs

To stop: double-click **`Stop-ERPDemo.bat`**

### Script Reference

| Script | Purpose |
|--------|---------|
| `Start-PrintJobSeeder.bat` | Start Print Job Seeder on port 5757 |
| `Stop-PrintJobSeeder.bat` | Stop the Print Job Seeder |
| `Start-ERPDemo.bat` | Start the Apex Industrial ERP Demo on port 5758 |
| `Stop-ERPDemo.bat` | Stop the ERP Demo |

---

## Quick Start — Mac / Linux

### One-time setup

Make the launcher scripts executable after cloning (only needs to be done once):

```bash
chmod +x Start-PrintJobSeeder.command Start-ERPDemo.command
chmod +x Start-PrintJobSeeder.sh Stop-PrintJobSeeder.sh
chmod +x Start-ERPDemo.sh Stop-ERPDemo.sh
```

### Print Job Seeder

**Double-click launcher (Mac):** Double-click **`Start-PrintJobSeeder.command`** in Finder. macOS opens a Terminal window, sets up the environment if needed, and starts the server.

**From the terminal:**
```bash
./Start-PrintJobSeeder.sh
```

Opens at **http://localhost:5757**. Click the gear icon to configure credentials, select industries, and click **Send Print Jobs**.

To stop: `./Stop-PrintJobSeeder.sh`

### ERP Demo

**Double-click launcher (Mac):** Double-click **`Start-ERPDemo.command`** in Finder.

**From the terminal:**
```bash
./Start-ERPDemo.sh
```

Opens at **http://localhost:5758**. Click **Admin** in the left sidebar to configure credentials.

To stop: `./Stop-ERPDemo.sh`

Shell scripts run in the background via `nohup`, writing logs to `printjobseeder.log` / `erp_demo.log` and saving a `.pid` file for clean shutdown.

> **Note on port 5000**: macOS Monterey and later reserves port 5000 for AirPlay Receiver. Both apps intentionally use ports 5757 and 5758 to avoid this conflict.

---

## Configuration

Both apps share the same `settings.json` file — configure once and both tools use the same credentials.

Open Settings via the **gear icon** in the Print Job Seeder or the **Admin** page in the ERP Demo.

### API Destinations

**API Cloud Link** — Connect to Vasion's cloud-hosted Output service:

| Region | Domain |
|--------|--------|
| US | printercloud.com |
| EMEA | printercloud5.com |
| ASIAPAC | printercloud10.com |
| Canada | printercloud15.com |
| SE-ASIAPAC | printercloud20.com |
| US-NOW | printercloudnow.com |

**On-Premise Output Service** — Connect to a self-hosted Output server. Configure server address, protocol (HTTP/HTTPS), port (default 443 for HTTPS, 31990 for HTTP), and bearer token.

**Manual** — Enter a custom API URL and token directly for testing or non-standard setups.

> 💡 Get your API key from the Vasion Admin Console: **Tools > Tokens > API Keys**

---

## Using the Print Job Seeder

After launching at **http://localhost:5757**:

1. **Configure Settings** (gear icon) — set API destination and credentials
2. **Select API Destination** — Cloud Link, On-Premise, or Manual
3. **Select Industries** — Healthcare, Manufacturing, Legal, Finance, Education (one or more)
4. **Choose PDF source** — Generate on-the-fly or upload your own
5. **Configure printers and filenames** — use presets or enter custom values
6. **Set job counts** and click **Send Print Jobs**

Progress streams in real time. Use the **Stop** button to cancel mid-run. If you close the browser and return, it reconnects to any in-progress run automatically.

### Automate All Mode

For the fastest demo setup:

1. Toggle **Automate All** in the industry selection card
2. Select your industries
3. Printers are fetched automatically from Vasion using the folder paths in Settings
4. Industry filenames and usernames are applied as presets
5. Set **Jobs per industry** and click **Send**

> ⚠️ Automate All requires API Cloud Link to be configured with an API key.

**Industry Folder Paths** — Configure wildcards in Settings to locate printers by folder:
- `*Healthcare*` — matches any folder containing "Healthcare"
- `*Manufacturing*` — matches any folder containing "Manufacturing"

---

## Using the ERP Demo

After launching at **http://localhost:5758**:

- **Dashboard** — KPI cards (Work Orders, Open POs, On-Time Delivery %, Print Jobs Today) and Chart.js charts for Orders Over Time and Print Job Volume
- **Orders** — Work Orders and Purchase Orders tables with status badges. Print individual rows or select multiple and bulk-print with real-time SSE progress
- **Customers** — 15 fake manufacturing companies with contacts and cities
- **Print Queue** — Single-job quick-send panel and a configurable background print run with live job log
- **Admin** — Settings page (same fields as the Seeder; writes to the shared `settings.json`)

### Fake Data

Generated at startup with a fixed seed for stable, consistent data across restarts:

- **30 Work Orders** — WO-XXXXX IDs, part numbers (e.g. `BKT-45821`), operators, statuses (Open / In Progress / Complete / On Hold)
- **20 Purchase Orders** — PO-XXXXX IDs, vendors, amounts, statuses (Pending / Approved / Received / Invoiced)
- **15 Customers** — Named manufacturing companies (e.g. Harrington Aerospace, Titan Automotive) with contacts and cities
- **Dashboard charts** — 30-day history, stable per process run

All print jobs from the ERP Demo use `@apexindustrial.com` email addresses.

---

## Industry Presets

Each industry includes **40 realistic filenames** with identifiers and **20 username presets** with fake but plausible email domains.

### Healthcare 🏥
Filenames include patient initials, record numbers, and department codes:
`Lab_Results_RWilliams_1847.pdf`, `Surgical_Consent_DMartin.pdf`, `MRI_Results_TKing_Brain.pdf`, and 37 more.

Usernames: `@mercyvalleymed.org`, `@stfrancishospital.net`, `@sunriseclinic.com`

### Manufacturing 🏭
Filenames include work order numbers, batch IDs, and equipment codes:
`Work_Order_WO78542.pdf`, `Quality_Inspection_QI2024_0892.pdf`, `Bill_of_Materials_BOM_A4521.pdf`, and 37 more.

Usernames: `@titansteelworks.com`, `@precisionmfg.net`, `@eagleassembly.com`

### Legal ⚖️
Filenames include case numbers, client initials, and matter codes:
`Contract_Agreement_CA2024_8847.pdf`, `Court_Filing_CF_Superior_4521.pdf`, `Deposition_Transcript_DT_Martinez.pdf`, and 37 more.

Usernames: `@sterlinglaw.com`, `@justiceattorneys.net`, `@oakwoodlegal.com`

### Finance 💰
Filenames include account numbers, client IDs, and report periods:
`Quarterly_Report_Q3_2024_Acct8847.pdf`, `Wire_Transfer_WT2024_89547.pdf`, `Portfolio_Analysis_PA_Chen.pdf`, and 37 more.

Usernames: `@summitfinancial.com`, `@keystonecapital.net`, `@harborwealth.com`

### Education 🎓
Filenames include student IDs, course codes, and semester info:
`Student_Transcript_ST_2024_78542.pdf`, `Course_Syllabus_CS_ENG101_Fall24.pdf`, `Financial_Aid_FA_Martinez_2024.pdf`, and 37 more.

Usernames: `@oakviewuniversity.edu`, `@lincolnhighschool.org`, `@mapleleafacademy.edu`

---

## PDF Generation

When using **Generate PDF**, the tool creates realistic multi-page documents with:

- **Industry-appropriate content** — medical records for healthcare, work orders for manufacturing, legal briefs for legal, etc.
- **Variable page counts** — 1–15 pages per job (configurable per industry)
- **Professional formatting** — headers, paragraphs, tables, and structured layouts
- **Unique content per job** — randomized details in each generated PDF

---

## Timing Modes

### Fixed Delay
Consistent delay between jobs (default: 1 second). Good for predictable, controlled testing.

### Natural / Random Timing
Randomized delays that simulate real user behavior:
- **50% of delays** — Quick succession (0.5–3 seconds), simulating batch printing
- **30% of delays** — Moderate gaps (3–30 seconds), normal work rhythm
- **20% of delays** — Longer pauses (30+ seconds up to max), coffee breaks and meetings

---

## Multi-Industry Workflow

Select multiple industries, configure each in its own tab, and all jobs are shuffled together before sending. Results show which industry each job belongs to — useful for demoing a mixed-use print environment (e.g., a hospital with medical, legal, and finance departments all printing simultaneously).

---

## Debugging & Logging

Both apps write detailed request/response logs to `request_log.txt` in the application folder.

**Watch logs in real-time on Windows (PowerShell):**
```powershell
Get-Content "request_log.txt" -Wait -Tail 50
```

**Watch logs in real-time on Mac/Linux:**
```bash
tail -f request_log.txt
```

The log includes:
- Full request URL
- HTTP headers (Authorization token masked for security)
- Form fields (filename, queue, username, copies)
- Response status code, headers, and body

---

## Requirements

- Python 3.8 or higher

## Manual Installation

If you prefer to set things up manually instead of using the launcher scripts:

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the Print Job Seeder (port 5757)
python app.py

# Run the ERP Demo (port 5758)
python app_erp.py
```

---

## API Reference

### Send a Print Job

```
POST {base_url}/v1/jobs
Authorization: Bearer {api_key_or_token}
Content-Type: multipart/form-data

- file: {PDF file}
- title: {printer name}
- copies: "1"
- username: {username}
```

### Fetch Printers

```
GET {base_url}/v1/printers?path={folder_path}&fields=id,title&limit=100
Authorization: Bearer {api_key}
```

The `path` parameter supports wildcards (e.g., `*Healthcare*`) to filter printers by folder location.

---

## Shared Module: print_utils.py

All print engine logic shared between `app.py` (Print Job Seeder) and `app_erp.py` (ERP Demo) lives in `print_utils.py`. This avoids duplication and ensures both apps behave identically.

**What's in `print_utils.py`:**
- Constants: `CLOUD_REGIONS`, `INDUSTRIES`, `INDUSTRY_PRESETS`, `USERNAME_PRESETS`, `INDUSTRY_CONTENT`, `LOREM_IPSUM`
- Settings helpers: `load_settings()`, `save_settings()`, `get_default_settings()`
- Key obfuscation: `obfuscate_key()`, `deobfuscate_key()`
- URL builders: `build_onprem_url()`, `get_cloud_base_url()`
- API: `fetch_printers_from_api()`
- PDF generation: `generate_pdf()`
- Timing: `generate_random_delay()`
- Job sending: `send_single_job()`, `send_single_job_from_buffer()`
- Logging: `log()`

### ERP Demo File Structure

| File | Purpose |
|------|---------|
| `app_erp.py` | Flask app (port 5758), fake data generators, all ERP routes and API endpoints |
| `templates/erp/base.html` | Enterprise layout: sidebar, header, cards, modals, toast system |
| `templates/erp/dashboard.html` | KPI cards + Chart.js charts + recent activity table |
| `templates/erp/orders.html` | Work Orders / Purchase Orders tabs with bulk print flow |
| `templates/erp/customers.html` | Customer accounts table |
| `templates/erp/print_queue.html` | Single job + bulk run panels with SSE streaming |
| `templates/erp/admin.html` | Settings admin page (connected to shared `settings.json`) |

---

## Notes

- Usernames, printers, and filenames cycle in round-robin fashion — if you have more jobs than entries in any list, it loops back to the beginning
- Generated PDFs are created in memory and cleaned up automatically
- All fake domains and names are fictional and not associated with real organizations
- Jobs from multiple industries are interleaved randomly to simulate realistic mixed traffic
- **Settings are stored locally** in `settings.json` — API keys are obfuscated (not plaintext) but treat this file as sensitive
- `settings.json` is excluded from git via `.gitignore`
