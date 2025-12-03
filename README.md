# Print Job Seeder

A utility for sending bulk print jobs to Vasion Output's API with industry-specific metadata. Perfect for populating the Output Console with realistic-looking print jobs for demos and testing.

## Features

- 🖨️ Send multiple print jobs to Vasion Output API
- 🏢 **Multi-industry support** - Configure and send jobs for multiple industries simultaneously
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
   - Start the Flask server
   - Automatically open the web interface in your browser

2. **Configure Global Settings:**
   - Enter your Vasion Output API URL
   - (Optional) Enter your Bearer token if authentication is required
   - Choose timing mode:
     - **Fixed Delay**: Consistent delay between jobs (configurable seconds)
     - **Natural/Random**: Randomized delays simulating real user behavior (bursts + gaps)

3. **Select Industries:**
   - Check one or more industries (Healthcare, Manufacturing, Legal, Finance, Education)
   - Each selected industry gets its own configuration tab

4. **Configure Each Industry Tab:**
   - Choose PDF source (Generate or Upload)
   - Use preset filenames or enter custom ones
   - Use preset usernames or enter custom ones
   - Enter printer names for that industry
   - Set number of jobs for that industry

5. **Click "Send Print Jobs"** and watch the progress!

## Batch Scripts

Three convenience scripts are provided for managing the application:

| Script | Purpose |
|--------|---------|
| `Start-PrintJobSeeder.bat` | Start the server (kills existing instances first, installs deps if needed) |
| `Stop-PrintJobSeeder.bat` | Stop the server cleanly |
| `Restart-PrintJobSeeder.bat` | Quick restart with log clearing (ideal for development) |

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

The tool sends multipart form POST requests in this format:

```
POST {url}
Authorization: {bearer_token}  (if provided)
Content-Type: multipart/form-data

- file: {uploaded PDF with new filename}
- queue: {printer name}
- copies: "1"
- username: {username}
```

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

## Notes

- The tool cycles through usernames, printers, and filenames in round-robin fashion within each industry
- If you have more jobs than entries in any list, it will loop back to the beginning
- Generated PDFs are created in memory and cleaned up automatically
- All fake domains and names are fictional and not associated with real organizations
- Jobs from multiple industries are interleaved randomly to simulate realistic mixed traffic
