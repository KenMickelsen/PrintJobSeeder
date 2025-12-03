# Print Job Seeder

A utility for sending bulk print jobs to Vasion Output's API with industry-specific metadata. Perfect for populating the Output Console with realistic-looking print jobs for demos and testing.

## Features

- 🖨️ Send multiple print jobs to Vasion Output API
- 🏥 Industry presets for Healthcare, Manufacturing, Legal, Finance, and Education
- 👥 Round-robin distribution of usernames, printers, and filenames
- 📊 Real-time progress tracking and job status logging
- 🔐 Optional Bearer token/API key authentication
- 🌐 Clean web interface

## Quick Start

1. **Double-click `Start-PrintJobSeeder.bat`** - This will:
   - Create a Python virtual environment (first run only)
   - Install all required dependencies (first run only)
   - Start the Flask server
   - Automatically open the web interface in your browser

2. **Fill in the form:**
   - Enter your Vasion Output API URL
   - (Optional) Enter your Bearer token if authentication is required
   - Upload a PDF file to use as the base document
   - Select an industry preset or enter custom filenames
   - Enter usernames (comma-separated)
   - Enter printer names that match your Vasion configuration
   - Set the number of jobs to send

3. **Click "Send Print Jobs"** and watch the progress!

## Requirements

- Python 3.8 or higher
- Windows (for the batch launcher)

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

### Healthcare 🏥
- Patient_Discharge_Summary.pdf
- Lab_Results_Report.pdf
- Insurance_Claim_Form.pdf
- Prescription_Order.pdf
- And 16 more...

### Manufacturing 🏭
- Work_Order_WO2024.pdf
- Quality_Inspection_Report.pdf
- Shipping_Manifest.pdf
- Bill_of_Materials.pdf
- And 16 more...

### Legal ⚖️
- Contract_Agreement.pdf
- Legal_Brief.pdf
- Court_Filing.pdf
- And 12 more...

### Finance 💰
- Quarterly_Report.pdf
- Annual_Statement.pdf
- Invoice.pdf
- And 12 more...

### Education 🎓
- Student_Transcript.pdf
- Report_Card.pdf
- Course_Syllabus.pdf
- And 12 more...

## Notes

- Jobs are sent with a 1-second delay
- The tool cycles through usernames, printers, and filenames in round-robin fashion
- If you have more jobs than entries in any list, it will loop back to the beginning
