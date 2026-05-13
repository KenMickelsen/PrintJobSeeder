# Print Job Seeder

A utility for sending bulk print jobs to Vasion Output's API with industry-specific metadata. Perfect for populating the Output Console with realistic-looking print jobs for demos and testing.

> **Also includes the [Apex Industrial ERP Demo](#apex-industrial-erp-demo) — a full fake manufacturing ERP UI that wraps the same print engine, great for customer-facing demos.**

## Features

- 🖨️ Send multiple print jobs to Vasion Output API
- 🏢 **Multi-industry support** - Configure and send jobs for multiple industries simultaneously
- 🔧 **Settings Management** - Persistent configuration for API credentials with secure storage
- 🌐 **Multiple API Destinations** - Support for Vasion Cloud regions, on-premise servers, or manual URLs
- 🤖 **Automate All Mode** - One-click automation that fetches printers and uses presets
- 📥 **Get Printers from Vasion** - Fetch printer lists directly from the API by industry folder path
- 📄 **Generate PDFs on-the-fly** with variable page counts (1-15 pages) and industry-specific content
- 📁 Upload your own PDF or let the tool generate realistic documents
- ⏱️ **Flexible timing options** - Fixed delays or randomized "natural" timing to simulate real users
- ⏹️ **Stop button** - Cancel job sending mid-process
- 🔄 **Session persistence** - Leave and return to see job progress (reconnects automatically)
- 🏥 Industry presets for Healthcare, Manufacturing, Legal, Finance, and Education
- 📝 **40 realistic filenames per industry** with identifiers (patient initials, work order numbers, case IDs, etc.)
- 👥 **20 username presets per industry** with realistic fake email domains
- 🔄 Round-robin distribution of usernames, printers, and filenames
- 🔀 Jobs from multiple industries are shuffled/interleaved for realistic mixed traffic
- 📊 Real-time progress tracking with streaming updates
- 🔐 Optional Bearer token/API key authentication
- 🌐 Clean tabbed web interface
- 📋 **Detailed request logging** for debugging API issues

## Quick Start

1. **Double-click `Start-PrintJobSeeder.bat`** - This will:
   - Kill any existing instances (prevents conflicts)
   - Create a Python virtual environment (first run only)
   - Install all required dependencies (first run only)
   - Start the Flask server on **port 5757**
   - Automatically open the web interface in your browser at `http://localhost:5757`

2. **Configure Settings (gear icon):**
   - **API Cloud Link**: Select your Vasion Cloud region and enter your API key
   - **On-Premise Output Service**: Configure server address, protocol, port, and bearer token
   - **Industry Folder Paths**: Set wildcard paths for fetching printers (e.g., `*Healthcare*`)
   
   > 💡 Get your API key from the Vasion Admin Console: **Tools > Tokens > API Keys**

3. **Select API Destination:**
   - **API Cloud Link**: Use Vasion's cloud service (US, EMEA, ASIAPAC, Canada, SE-ASIAPAC, US-NOW)
   - **On-Premise Output Service**: Connect to your own Output server
   - **Manual**: Enter a custom URL and token directly

4. **Select Industries:**
   - Check one or more industries (Healthcare, Manufacturing, Legal, Finance, Education)
   - Each selected industry gets its own configuration tab

5. **Quick Setup with Automate All:**
   - Toggle "Automate All" to enable one-click automation
   - Printers are automatically fetched from Vasion using folder paths
   - Presets are applied for filenames and usernames
   - Just set "Jobs per industry" and click Send!

6. **Or Configure Each Industry Manually:**
   - Choose PDF source (Generate or Upload)
   - Click "Get Printers from Vasion" or enter printer names manually
   - Use preset filenames/usernames or enter custom ones
   - Set number of jobs for that industry

7. **Click "Send Print Jobs"** and watch the progress!

## Batch Scripts (Windows)

Two convenience scripts are provided for managing the application:

| Script | Purpose |
|--------|---------|
| `Start-PrintJobSeeder.bat` | Start the server on port 5757 (kills existing instances first, installs deps if needed) |
| `Stop-PrintJobSeeder.bat` | Stop the server cleanly |
| `Start-ERPDemo.bat` | Start the Apex Industrial ERP Demo on port 5758 |
| `Stop-ERPDemo.bat` | Stop the ERP Demo |

## Mac / Linux

Shell script equivalents are included. Make them executable once, then run them directly:

```bash
chmod +x Start-PrintJobSeeder.sh Stop-PrintJobSeeder.sh
chmod +x Start-ERPDemo.sh Stop-ERPDemo.sh

# Start the Print Job Seeder (port 5757)
./Start-PrintJobSeeder.sh

# Start the ERP Demo (port 5758)
./Start-ERPDemo.sh
```

The shell scripts use `nohup` to run in the background and write logs to `printjobseeder.log` / `erp_demo.log`. A `.pid` file is created so the Stop script can cleanly terminate the process.

> **Note on port 5000**: macOS Monterey and later uses port 5000 for AirPlay Receiver. Both apps use different ports (5757 and 5758) to avoid this conflict.

## API Destinations

The tool supports three ways to connect to Vasion Output:

### API Cloud Link
Connect to Vasion's cloud-hosted Output service. Supported regions:

| Region | Domain |
|--------|--------|
| US | printercloud.com |
| EMEA | printercloud5.com |
| ASIAPAC | printercloud10.com |
| Canada | printercloud15.com |
| SE-ASIAPAC | printercloud20.com |
| US-NOW | printercloudnow.com |

### On-Premise Output Service
Connect to your own self-hosted Output server. Configure:
- Server address (hostname or IP)
- Protocol (HTTP or HTTPS)
- Port (default: 443 for HTTPS, 31990 for HTTP)
- Bearer token (if required)

### Manual
Enter a custom API URL and token directly for testing or non-standard setups.

## Automate All Mode

For quick demos, enable "Automate All" to streamline the process:

1. **Toggle Automate All** - The switch is in the industry selection card
2. **Select Industries** - Check the industries you want
3. **Printers Auto-Fetch** - The tool queries Vasion's API using the folder paths configured in Settings
4. **Presets Applied** - Industry-specific filenames and usernames are used automatically
5. **Set Jobs Per Industry** - Choose how many jobs to send for each selected industry
6. **Send!** - One click sends jobs for all selected industries

> ⚠️ Automate All requires API Cloud Link to be configured (with API key) for fetching printers.

### Industry Folder Paths

Configure folder path wildcards in Settings to tell the tool where to find printers for each industry. Examples:
- `*Healthcare*` - Matches any folder containing "Healthcare"
- `*Manufacturing*` - Matches any folder containing "Manufacturing"

These paths are used with the `GET /v1/printers?path=...` API to fetch printer lists.

## Debugging & Logging

The tool writes detailed request/response logs to `request_log.txt` in the application folder. This is helpful for debugging API issues (400 errors, authentication problems, etc.).

**To watch logs in real-time**, open PowerShell and run:
```powershell
Get-Content "j:\GitRepos\PrintJobSeeder\request_log.txt" -Wait -Tail 50
```

The log shows:
- Full request URL
- HTTP headers (Authorization token masked for security)
- Form fields (filename, queue, username, copies)
- Response status code
- Response headers and body

## Requirements

- Python 3.8 or higher
- Windows (for the batch launchers)

## Manual Installation (if needed)

If you prefer to set things up manually:

```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

## API Request Format

### Sending Print Jobs
The tool sends multipart form POST requests to submit print jobs:

```
POST {base_url}/v1/jobs
Authorization: Bearer {api_key_or_token}
Content-Type: multipart/form-data

- file: {PDF file}
- title: {printer name}
- copies: "1"
- username: {username}
```

### Fetching Printers
The tool can fetch printer lists from the Vasion API:

```
GET {base_url}/v1/printers?path={folder_path}&fields=id,title&limit=100
Authorization: Bearer {api_key}
```

The `path` parameter supports wildcards (e.g., `*Healthcare*`) to filter printers by folder location.

## Industry Presets

Each industry includes **40 realistic filenames** with identifiers and **20 username presets** with fake but plausible email domains.

### Healthcare 🏥
**Filenames** include patient initials, record numbers, and department codes:
- `Lab_Results_RWilliams_1847.pdf`
- `Surgical_Consent_DMartin.pdf`
- `MRI_Results_TKing_Brain.pdf`
- And 37 more...

**Usernames** use domains like `@mercyvalleymed.org`, `@stfrancishospital.net`, `@sunriseclinic.com`

### Manufacturing 🏭
**Filenames** include work order numbers, batch IDs, and equipment codes:
- `Work_Order_WO78542.pdf`
- `Quality_Inspection_QI2024_0892.pdf`
- `Bill_of_Materials_BOM_A4521.pdf`
- And 37 more...

**Usernames** use domains like `@titansteelworks.com`, `@precisionmfg.net`, `@eagleassembly.com`

### Legal ⚖️
**Filenames** include case numbers, client initials, and matter codes:
- `Contract_Agreement_CA2024_8847.pdf`
- `Court_Filing_CF_Superior_4521.pdf`
- `Deposition_Transcript_DT_Martinez.pdf`
- And 37 more...

**Usernames** use domains like `@sterlinglaw.com`, `@justiceattorneys.net`, `@oakwoodlegal.com`

### Finance 💰
**Filenames** include account numbers, client IDs, and report periods:
- `Quarterly_Report_Q3_2024_Acct8847.pdf`
- `Wire_Transfer_WT2024_89547.pdf`
- `Portfolio_Analysis_PA_Chen.pdf`
- And 37 more...

**Usernames** use domains like `@summitfinancial.com`, `@keystonecapital.net`, `@harborwealth.com`

### Education 🎓
**Filenames** include student IDs, course codes, and semester info:
- `Student_Transcript_ST_2024_78542.pdf`
- `Course_Syllabus_CS_ENG101_Fall24.pdf`
- `Financial_Aid_FA_Martinez_2024.pdf`
- And 37 more...

**Usernames** use domains like `@oakviewuniversity.edu`, `@lincolnhighschool.org`, `@mapleleafacademy.edu`

## PDF Generation

When using the **Generate PDF** option, the tool creates realistic multi-page documents with:

- **Industry-appropriate content**: Medical records for healthcare, work orders for manufacturing, legal briefs for legal, etc.
- **Variable page counts**: Each PDF randomly gets 1-15 pages (configurable per industry)
- **Professional formatting**: Headers, paragraphs, tables, and structured layouts
- **Unique content per job**: Each generated PDF has randomized details

## Timing Modes

### Fixed Delay
Jobs are sent with a consistent delay (default: 1 second) between each. Good for testing at a predictable pace.

### Natural/Random Timing
Jobs are sent with randomized delays to simulate real user behavior:
- **50% of delays**: Quick succession (0.5-3 seconds) - simulating batch printing
- **30% of delays**: Moderate gaps (3-30 seconds) - normal work rhythm
- **20% of delays**: Longer pauses (30+ seconds up to max) - coffee breaks, meetings, etc.

This creates realistic-looking traffic patterns with bursts of activity and natural lulls.

## Multi-Industry Workflow

The tool supports sending jobs for multiple industries simultaneously:

1. Select multiple industries from the checkbox list
2. Configure each industry in its own tab
3. Jobs from all industries are shuffled together before sending
4. Results show which industry each job belongs to

This is useful for demos showing a mixed-use print environment (e.g., a hospital with medical, legal, and finance departments).

## Apex Industrial ERP Demo

The `erp-demo` branch includes a second Flask application (`app_erp.py`) that wraps the same Vasion print engine inside a polished, customer-facing fake manufacturing ERP system called **Apex Industrial**.

This is designed for use during sales demos to show Vasion Output integrated naturally into an enterprise workflow — rather than as a standalone tool.

### What it looks like

The ERP UI is a clean, professional enterprise interface with:

- **Fixed left sidebar** — Apex Industrial branding, navy color scheme (`#1c3557`)
- **Dashboard** — 4 KPI cards (Work Orders, Open POs, On-Time Delivery %, Print Jobs Today) + two Chart.js charts (Orders Over Time, Print Job Volume)
- **Orders** — Work Orders and Purchase Orders tables with checkboxes, status badges, per-row Print buttons, and bulk-print with real-time SSE progress
- **Customers** — 15 fake manufacturing companies with contacts and cities
- **Print Queue** — Single-job quick-send and configurable background print run panels with live job log
- **Admin** — Full settings page (same fields as the main app: Cloud Link, On-Premise, industry paths)

### Running the ERP Demo

**Windows:**
```
Start-ERPDemo.bat
```

**Mac/Linux:**
```bash
./Start-ERPDemo.sh
```

Or manually:
```bash
source venv/bin/activate
python app_erp.py
```

Opens at **http://localhost:5758**.

### Architecture

| File | Purpose |
|------|---------|
| `app_erp.py` | Flask app (port 5758), fake data generators, all ERP routes and API endpoints |
| `templates/erp/base.html` | Enterprise layout: sidebar, header, cards, modals, toast system |
| `templates/erp/dashboard.html` | KPI cards + Chart.js charts + recent activity table |
| `templates/erp/orders.html` | Work Orders / Purchase Orders tabs with bulk print flow |
| `templates/erp/customers.html` | Customer accounts table |
| `templates/erp/print_queue.html` | Single job + bulk run panels with SSE streaming |
| `templates/erp/admin.html` | Settings admin page (connected to shared `settings.json`) |

### Fake Data

At startup, `app_erp.py` generates stable fake data (seeded with `random.seed(42)`):

- **30 Work Orders** — WO-XXXXX IDs, part numbers (e.g. `BKT-45821`), operators, customers, statuses (Open / In Progress / Complete / On Hold)
- **20 Purchase Orders** — PO-XXXXX IDs, vendors, amounts, buyer names, statuses (Pending / Approved / Received / Invoiced)
- **15 Customers** — Named manufacturing companies (e.g. Harrington Aerospace, Titan Automotive) with contacts and cities
- **Dashboard data** — 30-day chart history (randomized but stable per process), recent activity feed

All usernames in the manufacturing industry use `@apexindustrial.com` email addresses.

## Shared Module: print_utils.py

All print engine logic that is shared between `app.py` (Print Job Seeder) and `app_erp.py` (ERP Demo) lives in `print_utils.py`. This avoids duplication and ensures both apps behave identically.

**What's in `print_utils.py`:**
- All constants: `CLOUD_REGIONS`, `INDUSTRIES`, `INDUSTRY_PRESETS`, `USERNAME_PRESETS`, `INDUSTRY_CONTENT`, `LOREM_IPSUM`
- Settings helpers: `load_settings()`, `save_settings()`, `get_default_settings()`
- Key obfuscation: `obfuscate_key()`, `deobfuscate_key()`
- URL builders: `build_onprem_url()`, `get_cloud_base_url()`
- API: `fetch_printers_from_api()`
- PDF generation: `generate_pdf()`
- Timing: `generate_random_delay()`
- Print job sending: `send_single_job()`, `send_single_job_from_buffer()`
- Logging: `log()`

Both apps share the same `settings.json` file, so credentials configured in one app are available in the other.

## Notes

- The tool cycles through usernames, printers, and filenames in round-robin fashion within each industry
- If you have more jobs than entries in any list, it will loop back to the beginning
- Generated PDFs are created in memory and cleaned up automatically
- All fake domains and names are fictional and not associated with real organizations
- Jobs from multiple industries are interleaved randomly to simulate realistic mixed traffic
- **Settings are stored locally** in `settings.json` - API keys are obfuscated (not plaintext) but treat this file as sensitive
- The `settings.json` file is excluded from git via `.gitignore`
