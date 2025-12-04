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
import json
import threading
import uuid
import logging
import base64
from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Helper for immediate console output - writes to file AND stderr
import sys
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'request_log.txt')
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')

def log(message):
    """Print message to file and console"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {message}"
    # Write to file
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
    # Also try stderr
    sys.stderr.write(line + '\n')
    sys.stderr.flush()

# API Cloud Link region mappings
CLOUD_REGIONS = {
    'US': {
        'name': 'US',
        'domain': 'printercloud.com',
        'url': 'https://external-api.app.printercloud.com/v1/print'
    },
    'EMEA': {
        'name': 'EMEA',
        'domain': 'printercloud5.com',
        'url': 'https://external-api.app.printercloud5.com/v1/print'
    },
    'ASIAPAC': {
        'name': 'ASIAPAC',
        'domain': 'printercloud10.com',
        'url': 'https://external-api.app.printercloud10.com/v1/print'
    },
    'CANADA': {
        'name': 'CANADA',
        'domain': 'printercloud15.com',
        'url': 'https://external-api.app.printercloud15.com/v1/print'
    },
    'SE-ASIAPAC': {
        'name': 'SE-ASIAPAC',
        'domain': 'printercloud20.com',
        'url': 'https://external-api.app.printercloud20.com/v1/print'
    },
    'US-NOW': {
        'name': 'US-NOW',
        'domain': 'printercloudnow.com',
        'url': 'https://external-api.app.printercloudnow.com/v1/print'
    }
}

def get_default_settings():
    """Return default settings structure"""
    return {
        'cloud_link': {
            'region': '',
            'api_key': ''
        },
        'on_premise': {
            'server': '',
            'protocol': 'https',
            'port': '443',
            'bearer_token': ''
        },
        'industry_paths': {
            'healthcare': '*Healthcare*',
            'manufacturing': '*Manufacturing*',
            'legal': '*Legal*',
            'finance': '*Finance*',
            'education': '*Education*'
        }
    }

def load_settings():
    """Load settings from file"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                # Merge with defaults to ensure all keys exist
                defaults = get_default_settings()
                for section in defaults:
                    if section not in saved:
                        saved[section] = defaults[section]
                    else:
                        for key in defaults[section]:
                            if key not in saved[section]:
                                saved[section][key] = defaults[section][key]
                return saved
    except Exception as e:
        log(f"Error loading settings: {e}")
    return get_default_settings()

def save_settings(settings):
    """Save settings to file"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        log(f"Error saving settings: {e}")
        return False

def obfuscate_key(key):
    """Simple obfuscation for API keys (not true encryption, but prevents casual viewing)"""
    if not key:
        return ''
    return base64.b64encode(key.encode()).decode()

def deobfuscate_key(obfuscated):
    """Reverse the obfuscation"""
    if not obfuscated:
        return ''
    try:
        return base64.b64decode(obfuscated.encode()).decode()
    except:
        return obfuscated  # Return as-is if not obfuscated

def build_onprem_url(settings):
    """Build the on-premise URL from settings"""
    onprem = settings.get('on_premise', {})
    server = onprem.get('server', '').strip()
    protocol = onprem.get('protocol', 'https')
    port = onprem.get('port', '443').strip()
    
    if not server:
        return None
    
    # Build URL: protocol://server:port/v1/print
    url = f"{protocol}://{server}"
    if port and port not in ['80', '443']:
        url += f":{port}"
    elif port == '80' and protocol == 'https':
        url += f":{port}"
    elif port == '443' and protocol == 'http':
        url += f":{port}"
    url += "/v1/print"
    
    return url


def get_cloud_base_url(region):
    """Get the base URL for a cloud region (without endpoint path)"""
    if region not in CLOUD_REGIONS:
        return None
    domain = CLOUD_REGIONS[region]['domain']
    return f"https://external-api.app.{domain}"


def fetch_printers_from_api(api_key, base_url, path_filter):
    """Fetch all printers from the Vasion API matching the path filter"""
    all_printers = []
    page = 1
    limit = 100  # Fetch more per page to reduce API calls
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    while True:
        params = {
            'path': path_filter,
            'fields': 'id,title',
            'limit': limit,
            'page': page
        }
        
        try:
            log(f"Fetching printers: {base_url}/v1/printers?path={path_filter}&page={page}")
            response = requests.get(
                f"{base_url}/v1/printers",
                headers=headers,
                params=params,
                timeout=30
            )
            
            log(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                log(f"Error response: {response.text}")
                return None, f"API returned status {response.status_code}: {response.text[:200]}"
            
            data = response.json()
            printers = data.get('printers', [])
            pagination = data.get('pagination', {})
            
            # Extract printer titles
            for printer in printers:
                title = printer.get('title', '')
                if title:
                    all_printers.append(title)
            
            log(f"Page {page}: Found {len(printers)} printers, total so far: {len(all_printers)}")
            
            # Check if there are more pages
            total_pages = pagination.get('totalPages', 1)
            if page >= total_pages:
                break
            
            page += 1
            
        except requests.exceptions.Timeout:
            return None, "Request timed out"
        except Exception as e:
            log(f"Error fetching printers: {e}")
            return None, str(e)
    
    return all_printers, None


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size (multiple industry uploads)
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# Test log at startup
log("PrintJobSeeder starting up - logging initialized")

# Store active job sessions for streaming results
job_sessions = {}

# Available industries
INDUSTRIES = ['healthcare', 'manufacturing', 'legal', 'finance', 'education']

INDUSTRY_DISPLAY_NAMES = {
    'healthcare': '🏥 Healthcare',
    'manufacturing': '🏭 Manufacturing', 
    'legal': '⚖️ Legal',
    'finance': '💰 Finance',
    'education': '🎓 Education'
}

# Industry-specific filename presets (with realistic identifiers)
INDUSTRY_PRESETS = {
    "healthcare": [
        "Patient_Discharge_Summary_JSmith.pdf",
        "Lab_Results_RWilliams_1847.pdf",
        "Insurance_Claim_MCarter_2024.pdf",
        "Prescription_Order_KJohnson.pdf",
        "Medical_History_LAnderson.pdf",
        "Radiology_Report_BTaylor_XR4521.pdf",
        "Surgical_Consent_DMartin.pdf",
        "Patient_Intake_NThompson.pdf",
        "HIPAA_Authorization_SWhite.pdf",
        "Immunization_Record_JDavis_Peds.pdf",
        "Blood_Work_Results_MBrown_CBC.pdf",
        "Referral_Request_AWilson_Cardio.pdf",
        "Treatment_Plan_EGarcia_PT.pdf",
        "Physical_Therapy_Notes_RMoore.pdf",
        "Nursing_Assessment_CTaylor_ICU.pdf",
        "Medication_List_PJackson.pdf",
        "Allergy_Report_KLee_Updated.pdf",
        "Emergency_Contact_Form_JHarris.pdf",
        "Insurance_Verification_MClark.pdf",
        "Appointment_Summary_BRobinson.pdf",
        "Discharge_Instructions_LWalker_ER.pdf",
        "Consent_Form_DHall_Surgery.pdf",
        "Progress_Notes_JAllen_Day3.pdf",
        "Vital_Signs_Chart_SYoung.pdf",
        "MRI_Results_TKing_Brain.pdf",
        "CT_Scan_Report_NWright_Chest.pdf",
        "EKG_Results_MLopez_Routine.pdf",
        "Pathology_Report_RHill_Biopsy.pdf",
        "Consultation_Notes_AScott_Neuro.pdf",
        "Pre_Op_Checklist_JGreen_Hip.pdf",
        "Post_Op_Notes_CAdams_Knee.pdf",
        "Anesthesia_Record_DNelson.pdf",
        "Physical_Exam_KBaker_Annual.pdf",
        "Immunization_Schedule_ECampbell.pdf",
        "Diabetes_Management_RMitchell.pdf",
        "Cardiac_Clearance_TPerez_Pre.pdf",
        "Psych_Evaluation_JRoberts.pdf",
        "Wound_Care_Instructions_MTurner.pdf",
        "Lab_Requisition_SPhillips_STAT.pdf",
        "Patient_Education_LEvans_Asthma.pdf"
    ],
    "manufacturing": [
        "Work_Order_WO78542.pdf",
        "Quality_Inspection_QI2024_0892.pdf",
        "Shipping_Manifest_SM45721.pdf",
        "Bill_of_Materials_BOM_A4521.pdf",
        "Production_Schedule_PS_Week48.pdf",
        "Inventory_Report_INV_Dec2024.pdf",
        "Equipment_Maintenance_EM_CNC05.pdf",
        "Safety_Checklist_SC_LineA.pdf",
        "Packing_Slip_PKS89452.pdf",
        "Purchase_Order_PO2024_1847.pdf",
        "Vendor_Invoice_VI_Acme_8547.pdf",
        "Material_Requisition_MR7842.pdf",
        "Assembly_Instructions_AI_Model7.pdf",
        "Quality_Control_QC_Batch456.pdf",
        "Batch_Record_BR2024_0125.pdf",
        "Calibration_Certificate_CC_Gauge12.pdf",
        "Non_Conformance_NCR_4521.pdf",
        "Corrective_Action_CAR_2024_089.pdf",
        "Engineering_Change_ECO_5478.pdf",
        "Production_Report_PR_Nov28.pdf",
        "Work_Order_WO78543_Rush.pdf",
        "Bill_of_Lading_BOL_W86.pdf",
        "Receiving_Report_RR_12847.pdf",
        "Tool_Checkout_TC_Dept5.pdf",
        "Machine_Setup_MS_Lathe03.pdf",
        "First_Article_FAI_Part8847.pdf",
        "Inspection_Report_IR_Lot2847.pdf",
        "Traveler_Document_TD_Job4521.pdf",
        "Process_Sheet_PS_Weld_A7.pdf",
        "Routing_Sheet_RS_Assy_B12.pdf",
        "Scrap_Report_SR_Nov2024.pdf",
        "Rework_Order_RWO_4587.pdf",
        "Time_Sheet_TS_CNC_Dept.pdf",
        "Shift_Report_SR_Night_1202.pdf",
        "Downtime_Log_DT_Press04.pdf",
        "Preventive_Maint_PM_Weekly.pdf",
        "Lockout_Tagout_LOTO_M12.pdf",
        "SPC_Chart_SPC_Dim_A.pdf",
        "Gage_RnR_Study_GRR_0547.pdf",
        "PPAP_Document_PPAP_Cust_ABC.pdf"
    ],
    "legal": [
        "Contract_Agreement_Smith_v_Jones.pdf",
        "Legal_Brief_Case2024CV1847.pdf",
        "Court_Filing_Docket_45782.pdf",
        "Deposition_Transcript_RWilliams.pdf",
        "Settlement_Agreement_SA_4521.pdf",
        "Power_of_Attorney_POA_JDavis.pdf",
        "Affidavit_AFF_MJohnson_Signed.pdf",
        "Subpoena_SUB_2024_0892.pdf",
        "Discovery_Request_DR_Set2.pdf",
        "Motion_to_Dismiss_MTD_Filed.pdf",
        "Client_Engagement_CE_NewCo.pdf",
        "Case_Summary_CS_Anderson.pdf",
        "Witness_Statement_WS_BTaylor.pdf",
        "Evidence_Exhibit_EX_A_Photos.pdf",
        "Legal_Opinion_LO_Merger.pdf",
        "Retainer_Agreement_RA_Corp.pdf",
        "Complaint_Filed_CF_2024_1247.pdf",
        "Answer_Response_AR_Def.pdf",
        "Interrogatories_INT_Set1.pdf",
        "Request_Production_RFP_Docs.pdf",
        "Motion_Summary_MSJ_Plaintiff.pdf",
        "Opposition_Brief_OB_Filed.pdf",
        "Reply_Brief_RB_2024_089.pdf",
        "Trial_Exhibit_TE_List.pdf",
        "Jury_Instructions_JI_Draft.pdf",
        "Verdict_Form_VF_Civil.pdf",
        "Judgment_Entry_JE_Final.pdf",
        "Notice_Appeal_NOA_Filed.pdf",
        "Appellate_Brief_AB_Opening.pdf",
        "Trust_Document_TD_Family.pdf",
        "Will_Testament_WT_Estate.pdf",
        "Deed_Transfer_DT_Property.pdf",
        "Lease_Agreement_LA_Comm.pdf",
        "NDA_Agreement_NDA_TechCorp.pdf",
        "Employment_Contract_EC_Exec.pdf",
        "Shareholder_Agreement_SHA.pdf",
        "Articles_Incorporation_AOI.pdf",
        "Operating_Agreement_OA_LLC.pdf",
        "Patent_Application_PA_4587.pdf",
        "Trademark_Filing_TM_Brand.pdf"
    ],
    "finance": [
        "Quarterly_Report_Q3_2024.pdf",
        "Annual_Statement_FY2024.pdf",
        "Invoice_INV_2024_08547.pdf",
        "Account_Reconciliation_AR_Nov.pdf",
        "Budget_Proposal_BP_FY2025.pdf",
        "Expense_Report_ER_JSmith_Nov.pdf",
        "Tax_Filing_1120_2024.pdf",
        "Audit_Report_AR_External.pdf",
        "Financial_Forecast_FF_Q4.pdf",
        "Investment_Summary_IS_Port_A.pdf",
        "Loan_Application_LA_Comm.pdf",
        "Credit_Report_CR_NewCo.pdf",
        "Bank_Statement_BS_Oct2024.pdf",
        "Portfolio_Analysis_PA_Equity.pdf",
        "Risk_Assessment_RA_Market.pdf",
        "Balance_Sheet_BS_Nov2024.pdf",
        "Income_Statement_IS_YTD.pdf",
        "Cash_Flow_CF_Monthly.pdf",
        "Accounts_Payable_AP_Aging.pdf",
        "Accounts_Receivable_AR_Aging.pdf",
        "General_Ledger_GL_Detail.pdf",
        "Trial_Balance_TB_Nov2024.pdf",
        "Journal_Entry_JE_Adj_4521.pdf",
        "Depreciation_Schedule_DS.pdf",
        "Fixed_Assets_FA_Register.pdf",
        "Payroll_Summary_PS_Nov.pdf",
        "401k_Report_401k_Q3.pdf",
        "Benefits_Statement_BEN_2024.pdf",
        "Wire_Transfer_WT_Confirm.pdf",
        "Check_Register_CHK_Nov.pdf",
        "Credit_Memo_CM_2024_0847.pdf",
        "Debit_Memo_DM_Adj_125.pdf",
        "Purchase_Requisition_PR_Dept5.pdf",
        "Vendor_Payment_VP_Batch12.pdf",
        "Revenue_Report_RR_Region_W.pdf",
        "Variance_Analysis_VA_Nov.pdf",
        "Break_Even_Analysis_BEA.pdf",
        "Capital_Request_CR_Equip.pdf",
        "ROI_Analysis_ROI_Project_X.pdf",
        "Cost_Benefit_CBA_Initiative.pdf"
    ],
    "education": [
        "Student_Transcript_ST_JSmith.pdf",
        "Report_Card_RC_Grade5_Fall.pdf",
        "Course_Syllabus_CS_Math101.pdf",
        "Enrollment_Form_EF_2024_Fall.pdf",
        "Financial_Aid_FA_App_2025.pdf",
        "Recommendation_Letter_RL_JDavis.pdf",
        "Graduation_Certificate_GC_2024.pdf",
        "Class_Schedule_CS_Spring25.pdf",
        "Attendance_Report_AR_Nov.pdf",
        "Academic_Calendar_AC_2024_25.pdf",
        "Permission_Slip_PS_FieldTrip.pdf",
        "IEP_Document_IEP_MJohnson.pdf",
        "Test_Results_TR_SAT_BWilson.pdf",
        "Library_Checkout_LC_Patron457.pdf",
        "Student_Handbook_SH_2024_25.pdf",
        "Grade_Report_GR_Midterm.pdf",
        "Disciplinary_Record_DR_Incident.pdf",
        "Transfer_Request_TR_Student.pdf",
        "Degree_Audit_DA_BSmith.pdf",
        "Course_Registration_CR_Sp25.pdf",
        "Tuition_Statement_TS_Fall24.pdf",
        "Scholarship_Award_SA_Merit.pdf",
        "Parent_Conference_PC_Notes.pdf",
        "Progress_Report_PR_Week12.pdf",
        "Homework_Assignment_HW_Ch7.pdf",
        "Lesson_Plan_LP_Unit5_Math.pdf",
        "Curriculum_Guide_CG_Grade8.pdf",
        "Assessment_Rubric_AR_Essay.pdf",
        "Student_Evaluation_SE_Term1.pdf",
        "Teacher_Observation_TO_Smith.pdf",
        "Professional_Dev_PD_Workshop.pdf",
        "Field_Trip_Form_FT_Museum.pdf",
        "Athletic_Physical_AP_Sports.pdf",
        "Club_Roster_CR_Chess.pdf",
        "Yearbook_Order_YB_2025.pdf",
        "Lunch_Account_LA_Statement.pdf",
        "Bus_Route_BR_Schedule.pdf",
        "Emergency_Card_EC_Student.pdf",
        "Immunization_Record_IR_Req.pdf",
        "Graduation_Application_GA.pdf"
    ]
}

# Industry-specific username presets (with realistic domains)
USERNAME_PRESETS = {
    "healthcare": [
        "sarah.johnson@mercyvalleymed.org",
        "michael.chen@stlukeshealth.net",
        "jennifer.williams@cedarpinemedical.org",
        "david.martinez@regionalhealthpartners.com",
        "emily.brown@sunrisehospital.net",
        "robert.taylor@valleyviewclinic.org",
        "amanda.garcia@healthfirstcare.com",
        "christopher.lee@mountainmedgroup.net",
        "jessica.anderson@riverbendhealth.org",
        "matthew.wilson@communitycaremed.com",
        "ashley.thomas@northstarmedical.net",
        "daniel.jackson@lakesidehealth.org",
        "stephanie.white@praborahealthcare.com",
        "andrew.harris@blueskyclinic.net",
        "nicole.martin@westendmedical.org",
        "joshua.thompson@careloohospital.com",
        "rachel.moore@greenvalleymed.net",
        "brandon.clark@healthbridgecare.org",
        "michelle.rodriguez@pinecrestmedical.com",
        "kevin.lewis@harborviewhealth.net"
    ],
    "manufacturing": [
        "james.miller@apexmanufacturing.com",
        "linda.davis@precisionmetalworks.net",
        "william.garcia@summitindustries.com",
        "patricia.rodriguez@qualityforgeind.net",
        "richard.martinez@steelcraftmfg.com",
        "barbara.anderson@reliablemachine.net",
        "joseph.taylor@industrialpro.com",
        "susan.thomas@advancedalloys.net",
        "charles.hernandez@primeproduction.com",
        "margaret.moore@elitemanufacturing.net",
        "thomas.jackson@techfabindustries.com",
        "dorothy.martin@crestlineproducts.net",
        "christopher.lee@solidstatemfg.com",
        "nancy.white@pioneermachining.net",
        "daniel.harris@vanguardind.com",
        "karen.clark@northpointmfg.net",
        "mark.lewis@blueribbonfab.com",
        "betty.walker@keystoneworks.net",
        "steven.hall@frontierproducts.com",
        "helen.allen@dynamicmachine.net"
    ],
    "legal": [
        "elizabeth.parker@sterlinglaw.com",
        "william.brooks@hamiltonlegal.net",
        "catherine.murphy@crossmanpartners.com",
        "jonathan.cooper@meridianattorneys.net",
        "victoria.reed@hargrovelaw.com",
        "benjamin.ward@prestonlegalgroup.net",
        "alexandra.price@fairfieldlaw.com",
        "nicholas.kelly@summitlegaladvisors.net",
        "samantha.hughes@cavanaughlegal.com",
        "christopher.morgan@ridgewoodlaw.net",
        "olivia.foster@chamberspartners.com",
        "alexander.russell@northgatelegall.net",
        "natalie.barnes@peakstonelaw.com",
        "ryan.henderson@clearwaterlegal.net",
        "katherine.coleman@granitelegall.com",
        "tyler.jenkins@westbrooklawfirm.net",
        "lauren.patterson@silverdalelegal.com",
        "austin.simmons@baysidelawgroup.net",
        "megan.butler@oakridgeattorneys.com",
        "jacob.richardson@hartfordlegal.net"
    ],
    "finance": [
        "robert.campbell@oakgrovebank.com",
        "jennifer.mitchell@firsttrustfinancial.net",
        "michael.roberts@capitalhillpartners.com",
        "lisa.turner@bluestoneinvest.net",
        "david.phillips@harborfinancial.com",
        "maria.evans@summitcapitalgroup.net",
        "james.edwards@northstarbanking.com",
        "sandra.collins@keystonefinancial.net",
        "john.stewart@clearviewwealth.com",
        "nancy.sanchez@atlasfinancegroup.net",
        "steven.morris@ridgelinebank.com",
        "karen.rogers@premiuminvest.net",
        "paul.reed@vanguardfinancial.com",
        "donna.cook@ironwoodcapital.net",
        "mark.morgan@pinnaclefinance.com",
        "carol.bell@crescentbanking.net",
        "george.murphy@silverlakewealth.com",
        "ruth.bailey@horizonfinancial.net",
        "edward.rivera@foundationcapital.com",
        "sharon.cooper@tridentinvest.net"
    ],
    "education": [
        "mary.johnson@oakwoodacademy.edu",
        "james.smith@lincolnschools.org",
        "patricia.williams@maplegrovesd.edu",
        "john.brown@cedarvalleyschools.org",
        "jennifer.jones@willowcreekusd.edu",
        "michael.davis@pinehurstacademy.org",
        "linda.miller@sunriselearning.edu",
        "william.wilson@riversideschools.org",
        "elizabeth.moore@brightpathacademy.edu",
        "david.taylor@greenmeadowsd.org",
        "barbara.anderson@hillcrestschools.edu",
        "richard.thomas@valleycrestlearning.org",
        "susan.jackson@lakesideacademy.edu",
        "joseph.white@mountainviewusd.org",
        "margaret.harris@clearwaterschools.edu",
        "charles.martin@forestgroveed.org",
        "dorothy.thompson@springdaleschools.edu",
        "thomas.garcia@horizonacademy.org",
        "nancy.martinez@westfieldlearning.edu",
        "daniel.robinson@northwoodschools.org"
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
    settings = load_settings()
    # Don't expose actual API keys to frontend, just whether they're set
    settings_status = {
        'cloud_link': {
            'region': settings['cloud_link'].get('region', ''),
            'has_api_key': bool(settings['cloud_link'].get('api_key', ''))
        },
        'on_premise': {
            'server': settings['on_premise'].get('server', ''),
            'protocol': settings['on_premise'].get('protocol', 'https'),
            'port': settings['on_premise'].get('port', '443'),
            'has_bearer_token': bool(settings['on_premise'].get('bearer_token', ''))
        }
    }
    return render_template('index.html', 
                          presets=INDUSTRY_PRESETS, 
                          username_presets=USERNAME_PRESETS,
                          industries=INDUSTRIES,
                          industry_names=INDUSTRY_DISPLAY_NAMES,
                          cloud_regions=CLOUD_REGIONS,
                          settings_status=settings_status)


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings (with keys masked)"""
    settings = load_settings()
    defaults = get_default_settings()
    # Return masked version
    return jsonify({
        'cloud_link': {
            'region': settings['cloud_link'].get('region', ''),
            'api_key_set': bool(settings['cloud_link'].get('api_key', ''))
        },
        'on_premise': {
            'server': settings['on_premise'].get('server', ''),
            'protocol': settings['on_premise'].get('protocol', 'https'),
            'port': settings['on_premise'].get('port', '443'),
            'bearer_token_set': bool(settings['on_premise'].get('bearer_token', ''))
        },
        'industry_paths': settings.get('industry_paths', defaults['industry_paths']),
        'cloud_regions': CLOUD_REGIONS
    })


@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update settings"""
    try:
        data = request.get_json()
        current_settings = load_settings()
        
        # Update cloud link settings
        if 'cloud_link' in data:
            cl = data['cloud_link']
            if 'region' in cl:
                current_settings['cloud_link']['region'] = cl['region']
            if 'api_key' in cl and cl['api_key'] is not None:
                # Only update if a new key is provided (not empty string means clear, None means keep existing)
                current_settings['cloud_link']['api_key'] = obfuscate_key(cl['api_key'])
        
        # Update on-premise settings
        if 'on_premise' in data:
            op = data['on_premise']
            if 'server' in op:
                current_settings['on_premise']['server'] = op['server']
            if 'protocol' in op:
                current_settings['on_premise']['protocol'] = op['protocol']
            if 'port' in op:
                current_settings['on_premise']['port'] = op['port']
            if 'bearer_token' in op and op['bearer_token'] is not None:
                current_settings['on_premise']['bearer_token'] = obfuscate_key(op['bearer_token'])
        
        # Update industry paths
        if 'industry_paths' in data:
            if 'industry_paths' not in current_settings:
                current_settings['industry_paths'] = {}
            for industry, path in data['industry_paths'].items():
                current_settings['industry_paths'][industry] = path
        
        if save_settings(current_settings):
            return jsonify({'success': True, 'message': 'Settings saved'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save settings'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings/validate', methods=['GET'])
def validate_settings():
    """Validate current settings for each destination type"""
    settings = load_settings()
    
    cloud_valid = bool(
        settings['cloud_link'].get('region') and 
        settings['cloud_link'].get('api_key')
    )
    cloud_region = settings['cloud_link'].get('region', '')
    cloud_url = CLOUD_REGIONS.get(cloud_region, {}).get('url', '') if cloud_region else ''
    
    onprem_valid = bool(settings['on_premise'].get('server'))
    onprem_url = build_onprem_url(settings) if onprem_valid else ''
    onprem_has_token = bool(settings['on_premise'].get('bearer_token'))
    
    return jsonify({
        'cloud_link': {
            'valid': cloud_valid,
            'region': cloud_region,
            'url': cloud_url,
            'missing': [] if cloud_valid else (
                ['region'] if not settings['cloud_link'].get('region') else []
            ) + (
                ['api_key'] if not settings['cloud_link'].get('api_key') else []
            )
        },
        'on_premise': {
            'valid': onprem_valid,
            'url': onprem_url,
            'has_token': onprem_has_token,
            'missing': ['server'] if not onprem_valid else []
        }
    })


@app.route('/api/settings/get-auth', methods=['POST'])
def get_auth_for_destination():
    """Get the authentication token for a specific destination type (internal use only)"""
    try:
        data = request.get_json()
        dest_type = data.get('type')
        settings = load_settings()
        
        if dest_type == 'cloud':
            api_key = deobfuscate_key(settings['cloud_link'].get('api_key', ''))
            region = settings['cloud_link'].get('region', '')
            url = CLOUD_REGIONS.get(region, {}).get('url', '')
            return jsonify({
                'success': True,
                'url': url,
                'token': api_key
            })
        elif dest_type == 'onprem':
            token = deobfuscate_key(settings['on_premise'].get('bearer_token', ''))
            url = build_onprem_url(settings)
            return jsonify({
                'success': True,
                'url': url,
                'token': token
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid destination type'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/printers/<industry>', methods=['GET'])
def get_printers_for_industry(industry):
    """Fetch printers from Vasion API for a specific industry folder"""
    try:
        settings = load_settings()
        
        # Check if cloud link is configured
        region = settings['cloud_link'].get('region', '')
        api_key = deobfuscate_key(settings['cloud_link'].get('api_key', ''))
        
        if not region or not api_key:
            return jsonify({
                'success': False,
                'error': 'API Cloud Link must be configured to fetch printers. Please configure it in Settings.'
            }), 400
        
        # Get the path filter for this industry
        industry_paths = settings.get('industry_paths', get_default_settings()['industry_paths'])
        path_filter = industry_paths.get(industry, f'*{industry.capitalize()}*')
        
        if not path_filter:
            return jsonify({
                'success': False,
                'error': f'No folder path configured for {industry}'
            }), 400
        
        # Get the base URL for the cloud region
        base_url = get_cloud_base_url(region)
        if not base_url:
            return jsonify({
                'success': False,
                'error': f'Invalid cloud region: {region}'
            }), 400
        
        # Fetch printers
        printers, error = fetch_printers_from_api(api_key, base_url, path_filter)
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 400
        
        return jsonify({
            'success': True,
            'printers': printers,
            'count': len(printers),
            'path_filter': path_filter
        })
        
    except Exception as e:
        log(f"Error fetching printers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/presets', methods=['GET'])
def get_presets():
    """Return industry presets as JSON"""
    return jsonify({
        'filenames': INDUSTRY_PRESETS, 
        'usernames': USERNAME_PRESETS,
        'industries': INDUSTRIES,
        'industry_names': INDUSTRY_DISPLAY_NAMES
    })


def generate_random_delay(timing_mode, fixed_delay=1.0, min_delay=0.5, max_delay=120.0):
    """Generate a delay based on timing mode"""
    if timing_mode == 'fixed':
        return fixed_delay
    elif timing_mode == 'random':
        # Use exponential distribution weighted toward shorter delays
        # This creates "bursts" with occasional longer gaps
        rand = random.random()
        if rand < 0.5:
            # 50% chance: quick succession (0.5-3 seconds)
            return random.uniform(0.5, 3.0)
        elif rand < 0.8:
            # 30% chance: moderate gap (3-30 seconds)
            return random.uniform(3.0, 30.0)
        else:
            # 20% chance: longer gap (30 seconds to max_delay)
            return random.uniform(30.0, min(max_delay, 180.0))
    return 1.0


@app.route('/api/start-jobs', methods=['POST'])
def start_jobs():
    """Initialize a job session and return session ID for streaming"""
    global job_sessions
    
    log("=== /api/start-jobs called ===")
    
    try:
        # Get global settings
        url = request.form.get('url', '').strip()
        bearer_token = request.form.get('bearer_token', '').strip()
        log(f"URL: {url}")
        log(f"Bearer token present: {bool(bearer_token)}")
        
        # Timing settings
        timing_mode = request.form.get('timing_mode', 'fixed')
        fixed_delay = float(request.form.get('fixed_delay', 1.0))
        min_delay = float(request.form.get('min_delay', 0.5))
        max_delay = float(request.form.get('max_delay', 120.0))
        
        # Get active industries from JSON
        industry_configs_json = request.form.get('industry_configs', '{}')
        industry_configs = json.loads(industry_configs_json)
        
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        
        if not industry_configs:
            return jsonify({'success': False, 'error': 'At least one industry must be configured'}), 400
        
        # Build job queue from all industries
        all_jobs = []
        temp_files = {}  # Store uploaded files per industry
        
        for industry, config in industry_configs.items():
            num_jobs = int(config.get('num_jobs', 0))
            if num_jobs <= 0:
                continue
                
            usernames = [u.strip() for u in config.get('usernames', '').split(',') if u.strip()]
            printers = [p.strip() for p in config.get('printers', '').split(',') if p.strip()]
            filenames = [f.strip() for f in config.get('filenames', '').split(',') if f.strip()]
            pdf_source = config.get('pdf_source', 'generate')
            min_pages = int(config.get('min_pages', 1))
            max_pages = int(config.get('max_pages', 15))
            
            if not usernames:
                return jsonify({'success': False, 'error': f'{industry}: At least one username is required'}), 400
            if not printers:
                return jsonify({'success': False, 'error': f'{industry}: At least one printer is required'}), 400
            if not filenames:
                return jsonify({'success': False, 'error': f'{industry}: At least one filename is required'}), 400
            
            # Handle file upload for this industry
            temp_path = None
            if pdf_source == 'upload':
                file_key = f'file_{industry}'
                if file_key in request.files:
                    file = request.files[file_key]
                    if file.filename:
                        original_filename = secure_filename(file.filename)
                        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{industry}_{original_filename}')
                        file.save(temp_path)
                        temp_files[industry] = temp_path
                
                if not temp_path:
                    return jsonify({'success': False, 'error': f'{industry}: No file uploaded'}), 400
            
            # Create jobs for this industry
            for i in range(num_jobs):
                job = {
                    'industry': industry,
                    'username': usernames[i % len(usernames)],
                    'printer': printers[i % len(printers)],
                    'filename': filenames[i % len(filenames)],
                    'pdf_source': pdf_source,
                    'min_pages': min_pages,
                    'max_pages': max_pages,
                    'temp_path': temp_path
                }
                # Ensure filename ends with .pdf
                if not job['filename'].lower().endswith('.pdf'):
                    job['filename'] += '.pdf'
                all_jobs.append(job)
        
        if not all_jobs:
            return jsonify({'success': False, 'error': 'No jobs to send'}), 400
        
        # Shuffle jobs to interleave industries naturally
        random.shuffle(all_jobs)
        
        # Create session
        session_id = str(uuid.uuid4())
        job_sessions[session_id] = {
            'jobs': all_jobs,
            'results': [],
            'status': 'ready',
            'total': len(all_jobs),
            'completed': 0,
            'url': url,
            'bearer_token': bearer_token,
            'timing_mode': timing_mode,
            'fixed_delay': fixed_delay,
            'min_delay': min_delay,
            'max_delay': max_delay,
            'temp_files': temp_files,
            'stop_requested': False,
            'created_at': time.time()
        }
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'total_jobs': len(all_jobs)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stop-jobs/<session_id>', methods=['POST'])
def stop_jobs(session_id):
    """Stop a running job session"""
    global job_sessions
    
    if session_id not in job_sessions:
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    
    session = job_sessions[session_id]
    session['stop_requested'] = True
    session['status'] = 'stopping'
    
    return jsonify({
        'success': True,
        'message': 'Stop requested',
        'completed': session['completed'],
        'total': session['total']
    })


@app.route('/api/session-status/<session_id>')
def session_status(session_id):
    """Get the current status of a job session (for reconnection)"""
    global job_sessions
    
    if session_id not in job_sessions:
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    
    session = job_sessions[session_id]
    
    return jsonify({
        'success': True,
        'status': session['status'],
        'total': session['total'],
        'completed': session['completed'],
        'results': session['results'],
        'stop_requested': session.get('stop_requested', False)
    })


@app.route('/api/stream-jobs/<session_id>')
def stream_jobs(session_id):
    """Stream job results using Server-Sent Events"""
    log(f"=== /api/stream-jobs/{session_id} called ===")
    
    def generate():
        global job_sessions
        log(f"Generator started for session {session_id}")
        
        if session_id not in job_sessions:
            log(f"Session {session_id} not found!")
            yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
            return
        
        session = job_sessions[session_id]
        session['status'] = 'running'
        log(f"Session found. Jobs: {len(session['jobs'])}")
        
        all_jobs = session['jobs']
        url = session['url']
        bearer_token = session['bearer_token']
        timing_mode = session['timing_mode']
        fixed_delay = session['fixed_delay']
        min_delay = session['min_delay']
        max_delay = session['max_delay']
        temp_files = session['temp_files']
        total_jobs = len(all_jobs)
        
        for i, job in enumerate(all_jobs):
            # Check if stop was requested
            if session.get('stop_requested', False):
                session['status'] = 'stopped'
                success_count = sum(1 for r in session['results'] if r['success'])
                yield f"data: {json.dumps({'type': 'stopped', 'success_count': success_count, 'completed': session['completed'], 'total': total_jobs})}\n\n"
                # Clean up temp files
                for temp_path in temp_files.values():
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)
                return
            
            try:
                log(f"Processing job {i + 1}/{total_jobs}: {job['filename']} for {job['username']}")
                if job['pdf_source'] == 'generate':
                    # Generate a new PDF for each job
                    pdf_buffer = generate_pdf(job['filename'], job['industry'], job['min_pages'], job['max_pages'])
                    log(f"PDF generated, calling send_single_job_from_buffer...")
                    result = send_single_job_from_buffer(
                        url=url,
                        bearer_token=bearer_token,
                        file_buffer=pdf_buffer,
                        filename=job['filename'],
                        username=job['username'],
                        printer=job['printer'],
                        job_number=i + 1,
                        industry=job['industry']
                    )
                else:
                    # Use uploaded file
                    new_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f'job_{i}_{job["filename"]}')
                    shutil.copy(job['temp_path'], new_file_path)
                    
                    result = send_single_job(
                        url=url,
                        bearer_token=bearer_token,
                        file_path=new_file_path,
                        filename=job['filename'],
                        username=job['username'],
                        printer=job['printer'],
                        job_number=i + 1,
                        industry=job['industry']
                    )
                    
                    # Clean up the renamed file copy
                    if os.path.exists(new_file_path):
                        os.remove(new_file_path)
                
                session['results'].append(result)
                session['completed'] = i + 1
                
                # Send result to client
                yield f"data: {json.dumps({'type': 'job_result', 'result': result, 'progress': (i + 1) / total_jobs * 100})}\n\n"
                
                # Apply delay between jobs (except for the last one)
                if i < total_jobs - 1:
                    # Check stop during delay (check every 0.5 seconds)
                    delay = generate_random_delay(timing_mode, fixed_delay, min_delay, max_delay)
                    # Send delay info to client
                    yield f"data: {json.dumps({'type': 'delay', 'seconds': round(delay, 1)})}\n\n"
                    
                    # Sleep in small increments to allow stop checking
                    elapsed = 0
                    while elapsed < delay:
                        if session.get('stop_requested', False):
                            break
                        sleep_time = min(0.5, delay - elapsed)
                        time.sleep(sleep_time)
                        elapsed += sleep_time
                    
            except Exception as e:
                error_result = {
                    'job_number': i + 1,
                    'success': False,
                    'status_code': None,
                    'filename': job['filename'],
                    'username': job['username'],
                    'printer': job['printer'],
                    'industry': job['industry'],
                    'response': str(e)
                }
                session['results'].append(error_result)
                session['completed'] = i + 1
                yield f"data: {json.dumps({'type': 'job_result', 'result': error_result, 'progress': (i + 1) / total_jobs * 100})}\n\n"
        
        # Clean up temp files
        for temp_path in temp_files.values():
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        
        # Send completion message
        success_count = sum(1 for r in session['results'] if r['success'])
        yield f"data: {json.dumps({'type': 'complete', 'success_count': success_count, 'total': total_jobs})}\n\n"
        
        session['status'] = 'complete'
        
        # Clean up session after a delay (keep it around longer for reconnection)
        def cleanup():
            time.sleep(300)  # Keep session for 5 minutes for reconnection
            if session_id in job_sessions:
                del job_sessions[session_id]
        threading.Thread(target=cleanup, daemon=True).start()
    
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
    })


# Keep the old endpoint for backwards compatibility but mark deprecated
@app.route('/api/send-jobs', methods=['POST'])
def send_jobs():
    """Handle the print job submission for multiple industries (deprecated - use start-jobs + stream-jobs)"""
    global job_results
    job_results = []
    
    try:
        # Get global settings
        url = request.form.get('url', '').strip()
        bearer_token = request.form.get('bearer_token', '').strip()
        
        # Timing settings
        timing_mode = request.form.get('timing_mode', 'fixed')
        fixed_delay = float(request.form.get('fixed_delay', 1.0))
        min_delay = float(request.form.get('min_delay', 0.5))
        max_delay = float(request.form.get('max_delay', 120.0))
        
        # Get active industries from JSON
        industry_configs_json = request.form.get('industry_configs', '{}')
        industry_configs = json.loads(industry_configs_json)
        
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        
        if not industry_configs:
            return jsonify({'success': False, 'error': 'At least one industry must be configured'}), 400
        
        # Build job queue from all industries
        all_jobs = []
        temp_files = {}  # Store uploaded files per industry
        
        for industry, config in industry_configs.items():
            num_jobs = int(config.get('num_jobs', 0))
            if num_jobs <= 0:
                continue
                
            usernames = [u.strip() for u in config.get('usernames', '').split(',') if u.strip()]
            printers = [p.strip() for p in config.get('printers', '').split(',') if p.strip()]
            filenames = [f.strip() for f in config.get('filenames', '').split(',') if f.strip()]
            pdf_source = config.get('pdf_source', 'generate')
            min_pages = int(config.get('min_pages', 1))
            max_pages = int(config.get('max_pages', 15))
            
            if not usernames:
                return jsonify({'success': False, 'error': f'{industry}: At least one username is required'}), 400
            if not printers:
                return jsonify({'success': False, 'error': f'{industry}: At least one printer is required'}), 400
            if not filenames:
                return jsonify({'success': False, 'error': f'{industry}: At least one filename is required'}), 400
            
            # Handle file upload for this industry
            temp_path = None
            if pdf_source == 'upload':
                file_key = f'file_{industry}'
                if file_key in request.files:
                    file = request.files[file_key]
                    if file.filename:
                        original_filename = secure_filename(file.filename)
                        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{industry}_{original_filename}')
                        file.save(temp_path)
                        temp_files[industry] = temp_path
                
                if not temp_path:
                    return jsonify({'success': False, 'error': f'{industry}: No file uploaded'}), 400
            
            # Create jobs for this industry
            for i in range(num_jobs):
                job = {
                    'industry': industry,
                    'username': usernames[i % len(usernames)],
                    'printer': printers[i % len(printers)],
                    'filename': filenames[i % len(filenames)],
                    'pdf_source': pdf_source,
                    'min_pages': min_pages,
                    'max_pages': max_pages,
                    'temp_path': temp_path
                }
                # Ensure filename ends with .pdf
                if not job['filename'].lower().endswith('.pdf'):
                    job['filename'] += '.pdf'
                all_jobs.append(job)
        
        if not all_jobs:
            return jsonify({'success': False, 'error': 'No jobs to send'}), 400
        
        # Shuffle jobs to interleave industries naturally
        random.shuffle(all_jobs)
        
        # Send the jobs
        results = []
        total_jobs = len(all_jobs)
        
        for i, job in enumerate(all_jobs):
            if job['pdf_source'] == 'generate':
                # Generate a new PDF for each job
                pdf_buffer = generate_pdf(job['filename'], job['industry'], job['min_pages'], job['max_pages'])
                result = send_single_job_from_buffer(
                    url=url,
                    bearer_token=bearer_token,
                    file_buffer=pdf_buffer,
                    filename=job['filename'],
                    username=job['username'],
                    printer=job['printer'],
                    job_number=i + 1,
                    industry=job['industry']
                )
            else:
                # Use uploaded file
                new_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f'job_{i}_{job["filename"]}')
                shutil.copy(job['temp_path'], new_file_path)
                
                result = send_single_job(
                    url=url,
                    bearer_token=bearer_token,
                    file_path=new_file_path,
                    filename=job['filename'],
                    username=job['username'],
                    printer=job['printer'],
                    job_number=i + 1,
                    industry=job['industry']
                )
                
                # Clean up the renamed file copy
                if os.path.exists(new_file_path):
                    os.remove(new_file_path)
            
            results.append(result)
            
            # Apply delay between jobs (except for the last one)
            if i < total_jobs - 1:
                delay = generate_random_delay(timing_mode, fixed_delay, min_delay, max_delay)
                time.sleep(delay)
        
        # Clean up temp files
        for temp_path in temp_files.values():
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        
        job_results = results
        success_count = sum(1 for r in results if r['success'])
        
        return jsonify({
            'success': True,
            'message': f'Completed {success_count}/{total_jobs} jobs successfully',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def send_single_job(url, bearer_token, file_path, filename, username, printer, job_number, industry=''):
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
        
        # Log the request details
        log(f"")
        log(f"{'='*60}")
        log(f"JOB {job_number} - Sending request (from file)")
        log(f"  URL: {url}")
        log(f"  Method: POST")
        log(f"  Headers:")
        for key, value in headers.items():
            if key.lower() == 'authorization':
                log(f"    {key}: {value[:20]}..." if len(value) > 20 else f"    {key}: {value}")
            else:
                log(f"    {key}: {value}")
        log(f"  Form Fields:")
        log(f"    file: ({filename}, <{len(file_content)} bytes>, application/pdf)")
        log(f"    queue: {printer}")
        log(f"    copies: 1")
        log(f"    username: {username}")
        
        # Send the request
        response = requests.post(
            url,
            headers=headers,
            data=multipart_data,
            timeout=30
        )
        
        # Log the response
        log(f"  Response:")
        log(f"    Status Code: {response.status_code}")
        log(f"    Response Headers:")
        for key, value in response.headers.items():
            log(f"      {key}: {value}")
        log(f"    Response Body: {response.text[:1000] if response.text else '(empty)'}")
        log(f"{'='*60}")
        
        return {
            'job_number': job_number,
            'success': response.status_code in [200, 201, 202],
            'status_code': response.status_code,
            'filename': filename,
            'username': username,
            'printer': printer,
            'industry': industry,
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
            'industry': industry,
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
            'industry': industry,
            'response': str(e)
        }


def send_single_job_from_buffer(url, bearer_token, file_buffer, filename, username, printer, job_number, industry=''):
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
        
        # Log the request details
        log(f"")
        log(f"{'='*60}")
        log(f"JOB {job_number} - Sending request (generated PDF)")
        log(f"  URL: {url}")
        log(f"  Method: POST")
        log(f"  Headers:")
        for key, value in headers.items():
            if key.lower() == 'authorization':
                log(f"    {key}: {value[:20]}..." if len(value) > 20 else f"    {key}: {value}")
            else:
                log(f"    {key}: {value}")
        log(f"  Form Fields:")
        log(f"    file: ({filename}, <{len(file_content)} bytes>, application/pdf)")
        log(f"    queue: {printer}")
        log(f"    copies: 1")
        log(f"    username: {username}")
        
        # Send the request
        response = requests.post(
            url,
            headers=headers,
            data=multipart_data,
            timeout=30
        )
        
        # Log the response
        log(f"  Response:")
        log(f"    Status Code: {response.status_code}")
        log(f"    Response Headers:")
        for key, value in response.headers.items():
            log(f"      {key}: {value}")
        log(f"    Response Body: {response.text[:1000] if response.text else '(empty)'}")
        log(f"{'='*60}")
        
        return {
            'job_number': job_number,
            'success': response.status_code in [200, 201, 202],
            'status_code': response.status_code,
            'filename': filename,
            'username': username,
            'printer': printer,
            'industry': industry,
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
            'industry': industry,
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
            'industry': industry,
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
