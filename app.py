"""
Print Job Seeder - Flask Application
Sends multiple print jobs to Vasion Output API with industry-specific metadata
"""

import os
import io
import time
import random
import tempfile
import shutil
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# Industry-specific filename presets
INDUSTRY_PRESETS = {
    "healthcare": [
        "Patient_Discharge_Summary.pdf",
        "Lab_Results_Report.pdf",
        "Insurance_Claim_Form.pdf",
        "Prescription_Order.pdf",
        "Medical_History_Record.pdf",
        "Radiology_Report.pdf",
        "Surgical_Consent_Form.pdf",
        "Patient_Intake_Form.pdf",
        "HIPAA_Authorization.pdf",
        "Immunization_Record.pdf",
        "Blood_Work_Results.pdf",
        "Referral_Request.pdf",
        "Treatment_Plan.pdf",
        "Physical_Therapy_Notes.pdf",
        "Nursing_Assessment.pdf",
        "Medication_List.pdf",
        "Allergy_Report.pdf",
        "Emergency_Contact_Form.pdf",
        "Insurance_Verification.pdf",
        "Appointment_Summary.pdf"
    ],
    "manufacturing": [
        "Work_Order_WO2024.pdf",
        "Quality_Inspection_Report.pdf",
        "Shipping_Manifest.pdf",
        "Bill_of_Materials.pdf",
        "Production_Schedule.pdf",
        "Inventory_Report.pdf",
        "Equipment_Maintenance_Log.pdf",
        "Safety_Checklist.pdf",
        "Packing_Slip.pdf",
        "Purchase_Order.pdf",
        "Vendor_Invoice.pdf",
        "Material_Requisition.pdf",
        "Assembly_Instructions.pdf",
        "Quality_Control_Checklist.pdf",
        "Batch_Record.pdf",
        "Calibration_Certificate.pdf",
        "Non_Conformance_Report.pdf",
        "Corrective_Action_Request.pdf",
        "Engineering_Change_Order.pdf",
        "Production_Report.pdf"
    ],
    "legal": [
        "Contract_Agreement.pdf",
        "Legal_Brief.pdf",
        "Court_Filing.pdf",
        "Deposition_Transcript.pdf",
        "Settlement_Agreement.pdf",
        "Power_of_Attorney.pdf",
        "Affidavit.pdf",
        "Subpoena.pdf",
        "Discovery_Request.pdf",
        "Motion_to_Dismiss.pdf",
        "Client_Engagement_Letter.pdf",
        "Case_Summary.pdf",
        "Witness_Statement.pdf",
        "Evidence_Exhibit.pdf",
        "Legal_Opinion.pdf"
    ],
    "finance": [
        "Quarterly_Report.pdf",
        "Annual_Statement.pdf",
        "Invoice.pdf",
        "Account_Reconciliation.pdf",
        "Budget_Proposal.pdf",
        "Expense_Report.pdf",
        "Tax_Filing.pdf",
        "Audit_Report.pdf",
        "Financial_Forecast.pdf",
        "Investment_Summary.pdf",
        "Loan_Application.pdf",
        "Credit_Report.pdf",
        "Bank_Statement.pdf",
        "Portfolio_Analysis.pdf",
        "Risk_Assessment.pdf"
    ],
    "education": [
        "Student_Transcript.pdf",
        "Report_Card.pdf",
        "Course_Syllabus.pdf",
        "Enrollment_Form.pdf",
        "Financial_Aid_Application.pdf",
        "Recommendation_Letter.pdf",
        "Graduation_Certificate.pdf",
        "Class_Schedule.pdf",
        "Attendance_Report.pdf",
        "Academic_Calendar.pdf",
        "Parent_Permission_Slip.pdf",
        "IEP_Document.pdf",
        "Test_Results.pdf",
        "Library_Checkout.pdf",
        "Student_Handbook.pdf"
    ]
}

# Industry-specific content templates for PDF generation
INDUSTRY_CONTENT = {
    "healthcare": {
        "headers": [
            "PATIENT INFORMATION FORM", "MEDICAL RECORD", "CLINICAL REPORT",
            "HEALTHCARE DOCUMENT", "PATIENT CHART", "MEDICAL SUMMARY"
        ],
        "fields": [
            ("Patient Name", "________________________________"),
            ("Date of Birth", "____ / ____ / ________"),
            ("Medical Record #", "MRN-______________"),
            ("Attending Physician", "Dr. ________________"),
            ("Department", "________________________________"),
            ("Insurance Provider", "________________________________"),
            ("Policy Number", "________________________________"),
            ("Primary Diagnosis", "________________________________"),
            ("Date of Service", "____ / ____ / ________"),
        ],
        "paragraphs": [
            "This document contains protected health information (PHI) as defined by HIPAA regulations. Unauthorized disclosure is prohibited.",
            "Patient presented with symptoms consistent with the documented diagnosis. Physical examination was performed and findings are recorded below.",
            "Treatment plan has been discussed with patient and/or authorized representative. Informed consent obtained for all procedures.",
            "Vital signs within normal limits unless otherwise noted. Patient tolerated procedure well with no immediate complications.",
            "Follow-up appointment scheduled. Patient instructed on medication regimen, potential side effects, and warning signs requiring immediate attention.",
            "Laboratory results have been reviewed and are consistent with clinical presentation. Further testing may be indicated based on response to treatment.",
            "Medication reconciliation completed. Current medications verified with patient and updated in electronic health record.",
            "Discharge instructions provided to patient. Patient verbalized understanding of care plan and follow-up requirements.",
        ],
        "table_headers": ["Date", "Procedure", "Provider", "Notes"],
        "table_data": [
            ["12/01/2024", "Initial Consultation", "Dr. Smith", "Complete"],
            ["12/02/2024", "Laboratory Work", "Lab Tech", "Results Pending"],
            ["12/03/2024", "Follow-up Visit", "Dr. Johnson", "Scheduled"],
        ]
    },
    "manufacturing": {
        "headers": [
            "PRODUCTION DOCUMENT", "QUALITY CONTROL REPORT", "WORK ORDER",
            "MANUFACTURING RECORD", "INSPECTION REPORT", "OPERATIONS LOG"
        ],
        "fields": [
            ("Work Order #", "WO-______________"),
            ("Part Number", "PN-______________"),
            ("Batch/Lot #", "LOT-______________"),
            ("Production Date", "____ / ____ / ________"),
            ("Operator ID", "________________________________"),
            ("Machine/Line", "________________________________"),
            ("Quantity Produced", "________________________________"),
            ("Quality Inspector", "________________________________"),
            ("Shift", "☐ Day  ☐ Swing  ☐ Night"),
        ],
        "paragraphs": [
            "This document serves as the official production record for the referenced work order. All entries must be made in permanent ink.",
            "Quality inspection completed per standard operating procedures. All measurements within specified tolerances unless noted.",
            "Raw materials verified against bill of materials. Material lot numbers recorded for traceability purposes.",
            "Equipment calibration verified prior to production run. Calibration certificates on file in quality assurance department.",
            "Production parameters monitored throughout run. Any deviations from standard process documented in remarks section.",
            "Finished goods inspection completed. Product meets all quality specifications and is approved for release to inventory.",
            "Non-conforming material identified and segregated. Disposition pending review by quality engineering team.",
            "Preventive maintenance completed as scheduled. Equipment returned to production-ready status.",
        ],
        "table_headers": ["Step", "Operation", "Time", "Status"],
        "table_data": [
            ["1", "Material Prep", "08:00", "Complete"],
            ["2", "Assembly", "09:30", "Complete"],
            ["3", "Quality Check", "11:00", "In Progress"],
            ["4", "Packaging", "13:00", "Pending"],
        ]
    },
    "legal": {
        "headers": [
            "LEGAL DOCUMENT", "CONFIDENTIAL MEMORANDUM", "CASE FILE",
            "ATTORNEY WORK PRODUCT", "PRIVILEGED COMMUNICATION", "LEGAL BRIEF"
        ],
        "fields": [
            ("Case Number", "________________________________"),
            ("Matter Name", "________________________________"),
            ("Client Name", "________________________________"),
            ("Responsible Attorney", "________________________________"),
            ("Date Filed", "____ / ____ / ________"),
            ("Court/Jurisdiction", "________________________________"),
            ("Opposing Counsel", "________________________________"),
            ("Document Type", "________________________________"),
            ("Confidentiality", "☐ Public  ☐ Confidential  ☐ Privileged"),
        ],
        "paragraphs": [
            "ATTORNEY-CLIENT PRIVILEGED AND CONFIDENTIAL. This document is protected by attorney-client privilege and/or work product doctrine.",
            "This memorandum summarizes the relevant legal issues and provides analysis based on applicable statutes and case law.",
            "The facts presented herein are based on information provided by the client and documentation reviewed to date.",
            "Legal research has been conducted regarding the applicable jurisdiction's treatment of the issues presented.",
            "Based on our analysis, we recommend the following course of action, subject to further developments in the matter.",
            "Discovery requests have been prepared and are ready for service upon opposing counsel pending client approval.",
            "Settlement negotiations remain ongoing. The opposing party has indicated willingness to discuss resolution.",
            "Court deadlines and statute of limitations dates have been calendared. All filings are current.",
        ],
        "table_headers": ["Date", "Event", "Deadline", "Status"],
        "table_data": [
            ["12/15/2024", "Discovery Due", "01/15/2025", "In Progress"],
            ["01/20/2025", "Motion Hearing", "01/20/2025", "Scheduled"],
            ["02/01/2025", "Trial Date", "02/01/2025", "Confirmed"],
        ]
    },
    "finance": {
        "headers": [
            "FINANCIAL REPORT", "ACCOUNT STATEMENT", "FISCAL DOCUMENT",
            "FINANCIAL SUMMARY", "BUDGET REPORT", "ACCOUNTING RECORD"
        ],
        "fields": [
            ("Account Number", "________________________________"),
            ("Report Period", "____ / ____ / ________ to ____ / ____ / ________"),
            ("Prepared By", "________________________________"),
            ("Department", "________________________________"),
            ("Cost Center", "________________________________"),
            ("Approval Status", "☐ Draft  ☐ Reviewed  ☐ Approved"),
            ("Report Date", "____ / ____ / ________"),
            ("Currency", "________________________________"),
            ("Fiscal Year", "FY __________"),
        ],
        "paragraphs": [
            "This financial report has been prepared in accordance with generally accepted accounting principles (GAAP).",
            "All figures presented are subject to final audit adjustments. Preliminary numbers may vary from audited statements.",
            "Revenue recognition follows the accrual method of accounting. Expenses are matched to the period in which they are incurred.",
            "Budget variances exceeding 10% have been reviewed with department managers. Explanations are provided in the notes section.",
            "Cash flow projections are based on historical patterns and known upcoming obligations.",
            "Accounts receivable aging analysis indicates collection efforts are proceeding within normal parameters.",
            "Capital expenditure requests have been evaluated against available budget and strategic priorities.",
            "Internal controls have been tested and are operating effectively. No material weaknesses identified.",
        ],
        "table_headers": ["Category", "Budget", "Actual", "Variance"],
        "table_data": [
            ["Revenue", "$500,000", "$485,000", "($15,000)"],
            ["Expenses", "$350,000", "$340,000", "$10,000"],
            ["Net Income", "$150,000", "$145,000", "($5,000)"],
        ]
    },
    "education": {
        "headers": [
            "ACADEMIC DOCUMENT", "STUDENT RECORD", "EDUCATIONAL REPORT",
            "SCHOOL DOCUMENT", "ACADEMIC RECORD", "ENROLLMENT FORM"
        ],
        "fields": [
            ("Student Name", "________________________________"),
            ("Student ID", "________________________________"),
            ("Grade Level", "________________________________"),
            ("School Year", "20____ - 20____"),
            ("Teacher/Instructor", "________________________________"),
            ("Course/Subject", "________________________________"),
            ("Parent/Guardian", "________________________________"),
            ("Emergency Contact", "________________________________"),
            ("Date", "____ / ____ / ________"),
        ],
        "paragraphs": [
            "This document is part of the official student record and is protected under FERPA regulations.",
            "Academic performance has been evaluated based on established curriculum standards and learning objectives.",
            "Student demonstrates consistent effort and engagement in classroom activities and assignments.",
            "Areas for improvement have been identified and discussed with student and parent/guardian as appropriate.",
            "Standardized assessment results are included in the supplementary materials section of this report.",
            "Attendance records indicate the student has met minimum requirements for course credit.",
            "Recommendations for academic support services have been made based on observed needs.",
            "Parent/guardian conference scheduled to discuss student progress and educational goals.",
        ],
        "table_headers": ["Subject", "Grade", "Credits", "Status"],
        "table_data": [
            ["Mathematics", "B+", "3.0", "Complete"],
            ["English", "A-", "3.0", "Complete"],
            ["Science", "B", "3.0", "In Progress"],
            ["History", "A", "3.0", "Complete"],
        ]
    }
}

# Lorem ipsum for filler text
LOREM_IPSUM = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
    "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium.",
    "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores.",
    "Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit.",
    "Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit laboriosam.",
]


def generate_pdf(filename, industry, min_pages=1, max_pages=15):
    """Generate a PDF with random content based on industry"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=72)
    
    # Get industry content or use generic
    content_template = INDUSTRY_CONTENT.get(industry, INDUSTRY_CONTENT.get("healthcare"))
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceBefore=6,
        spaceAfter=6,
        leading=14
    )
    
    field_style = ParagraphStyle(
        'FieldStyle',
        parent=styles['Normal'],
        fontSize=11,
        spaceBefore=8,
        spaceAfter=8
    )
    
    story = []
    num_pages = random.randint(min_pages, max_pages)
    
    # Generate content for each page
    for page_num in range(num_pages):
        if page_num > 0:
            story.append(PageBreak())
        
        # Page header
        header = random.choice(content_template["headers"])
        story.append(Paragraph(header, title_style))
        
        # Document reference
        doc_ref = f"Document: {filename.replace('.pdf', '')} | Page {page_num + 1} of {num_pages}"
        story.append(Paragraph(doc_ref, ParagraphStyle('DocRef', parent=styles['Normal'], 
                                                        fontSize=9, textColor=colors.gray, 
                                                        alignment=TA_CENTER)))
        story.append(Spacer(1, 20))
        
        # Randomly decide what content to include on this page
        content_types = random.sample(['fields', 'paragraphs', 'table', 'lorem'], 
                                      k=random.randint(2, 4))
        
        for content_type in content_types:
            if content_type == 'fields':
                story.append(Paragraph("INFORMATION", heading_style))
                # Add 3-6 random fields
                fields = random.sample(content_template["fields"], 
                                      k=min(random.randint(3, 6), len(content_template["fields"])))
                for field_name, field_value in fields:
                    story.append(Paragraph(f"<b>{field_name}:</b> {field_value}", field_style))
                story.append(Spacer(1, 15))
                
            elif content_type == 'paragraphs':
                story.append(Paragraph("DETAILS", heading_style))
                # Add 2-4 random paragraphs
                paragraphs = random.sample(content_template["paragraphs"], 
                                          k=min(random.randint(2, 4), len(content_template["paragraphs"])))
                for para in paragraphs:
                    story.append(Paragraph(para, normal_style))
                story.append(Spacer(1, 15))
                
            elif content_type == 'table':
                story.append(Paragraph("SUMMARY", heading_style))
                # Create a table
                table_data = [content_template["table_headers"]] + content_template["table_data"]
                table = Table(table_data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 1.2*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ]))
                story.append(table)
                story.append(Spacer(1, 20))
                
            elif content_type == 'lorem':
                story.append(Paragraph("ADDITIONAL NOTES", heading_style))
                # Add some lorem ipsum
                lorem_paras = random.sample(LOREM_IPSUM, k=random.randint(2, 4))
                for para in lorem_paras:
                    story.append(Paragraph(para, normal_style))
                story.append(Spacer(1, 15))
    
    # Build the PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


# Store job results for the current session
job_results = []


@app.route('/')
def index():
    """Render the main web interface"""
    return render_template('index.html', presets=INDUSTRY_PRESETS)


@app.route('/api/presets', methods=['GET'])
def get_presets():
    """Return industry presets as JSON"""
    return jsonify(INDUSTRY_PRESETS)


@app.route('/api/send-jobs', methods=['POST'])
def send_jobs():
    """Handle the print job submission"""
    global job_results
    job_results = []
    
    try:
        # Get form data
        url = request.form.get('url', '').strip()
        bearer_token = request.form.get('bearer_token', '').strip()
        usernames = [u.strip() for u in request.form.get('usernames', '').split(',') if u.strip()]
        printers = [p.strip() for p in request.form.get('printers', '').split(',') if p.strip()]
        filenames = [f.strip() for f in request.form.get('filenames', '').split(',') if f.strip()]
        num_jobs = int(request.form.get('num_jobs', 1))
        
        # PDF source options
        pdf_source = request.form.get('pdf_source', 'upload')
        industry = request.form.get('industry', 'healthcare')
        min_pages = int(request.form.get('min_pages', 1))
        max_pages = int(request.form.get('max_pages', 15))
        
        # Validate required fields
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        if not usernames:
            return jsonify({'success': False, 'error': 'At least one username is required'}), 400
        if not printers:
            return jsonify({'success': False, 'error': 'At least one printer is required'}), 400
        if not filenames:
            return jsonify({'success': False, 'error': 'At least one filename is required'}), 400
        
        temp_path = None
        
        # Handle file source
        if pdf_source == 'upload':
            # Handle file upload
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file uploaded'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'No file selected'}), 400
            
            # Save the uploaded file temporarily
            original_filename = secure_filename(file.filename)
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
            file.save(temp_path)
        
        # Send the jobs
        results = []
        for i in range(num_jobs):
            # Round-robin selection
            username = usernames[i % len(usernames)]
            printer = printers[i % len(printers)]
            filename = filenames[i % len(filenames)]
            
            # Ensure filename ends with .pdf
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            
            if pdf_source == 'generate':
                # Generate a new PDF for each job
                pdf_buffer = generate_pdf(filename, industry, min_pages, max_pages)
                result = send_single_job_from_buffer(
                    url=url,
                    bearer_token=bearer_token,
                    file_buffer=pdf_buffer,
                    filename=filename,
                    username=username,
                    printer=printer,
                    job_number=i + 1
                )
            else:
                # Use uploaded file - create a copy with the new name
                new_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                shutil.copy(temp_path, new_file_path)
                
                result = send_single_job(
                    url=url,
                    bearer_token=bearer_token,
                    file_path=new_file_path,
                    filename=filename,
                    username=username,
                    printer=printer,
                    job_number=i + 1
                )
                
                # Clean up the renamed file copy
                if os.path.exists(new_file_path) and new_file_path != temp_path:
                    os.remove(new_file_path)
            
            results.append(result)
            
            # Delay between jobs (except for the last one)
            if i < num_jobs - 1:
                time.sleep(1)
        
        # Clean up the original temp file if uploaded
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        
        job_results = results
        success_count = sum(1 for r in results if r['success'])
        
        return jsonify({
            'success': True,
            'message': f'Completed {success_count}/{num_jobs} jobs successfully',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def send_single_job(url, bearer_token, file_path, filename, username, printer, job_number):
    """Send a single print job to the API from a file path"""
    try:
        # Prepare headers
        headers = {}
        if bearer_token:
            headers['Authorization'] = bearer_token
        
        # Prepare multipart form data
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        multipart_data = MultipartEncoder(
            fields={
                'file': (filename, file_content, 'application/pdf'),
                'queue': printer,
                'copies': '1',
                'username': username
            }
        )
        
        headers['Content-Type'] = multipart_data.content_type
        
        # Send the request
        response = requests.post(
            url,
            headers=headers,
            data=multipart_data,
            timeout=30
        )
        
        return {
            'job_number': job_number,
            'success': response.status_code in [200, 201, 202],
            'status_code': response.status_code,
            'filename': filename,
            'username': username,
            'printer': printer,
            'response': response.text[:500] if response.text else ''
        }
        
    except requests.exceptions.Timeout:
        return {
            'job_number': job_number,
            'success': False,
            'status_code': None,
            'filename': filename,
            'username': username,
            'printer': printer,
            'response': 'Request timed out'
        }
    except Exception as e:
        return {
            'job_number': job_number,
            'success': False,
            'status_code': None,
            'filename': filename,
            'username': username,
            'printer': printer,
            'response': str(e)
        }


def send_single_job_from_buffer(url, bearer_token, file_buffer, filename, username, printer, job_number):
    """Send a single print job to the API from an in-memory buffer"""
    try:
        # Prepare headers
        headers = {}
        if bearer_token:
            headers['Authorization'] = bearer_token
        
        # Get file content from buffer
        file_content = file_buffer.read()
        
        multipart_data = MultipartEncoder(
            fields={
                'file': (filename, file_content, 'application/pdf'),
                'queue': printer,
                'copies': '1',
                'username': username
            }
        )
        
        headers['Content-Type'] = multipart_data.content_type
        
        # Send the request
        response = requests.post(
            url,
            headers=headers,
            data=multipart_data,
            timeout=30
        )
        
        return {
            'job_number': job_number,
            'success': response.status_code in [200, 201, 202],
            'status_code': response.status_code,
            'filename': filename,
            'username': username,
            'printer': printer,
            'response': response.text[:500] if response.text else ''
        }
        
    except requests.exceptions.Timeout:
        return {
            'job_number': job_number,
            'success': False,
            'status_code': None,
            'filename': filename,
            'username': username,
            'printer': printer,
            'response': 'Request timed out'
        }
    except Exception as e:
        return {
            'job_number': job_number,
            'success': False,
            'status_code': None,
            'filename': filename,
            'username': username,
            'printer': printer,
            'response': str(e)
        }


@app.route('/api/results', methods=['GET'])
def get_results():
    """Return the current job results"""
    return jsonify(job_results)


if __name__ == '__main__':
    print("=" * 50)
    print("Print Job Seeder")
    print("=" * 50)
    print("Starting server at http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Open browser automatically
    import webbrowser
    import threading
    
    def open_browser():
        time.sleep(1.5)  # Wait for server to start
        webbrowser.open('http://localhost:5000')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    app.run(debug=False, host='localhost', port=5000)
