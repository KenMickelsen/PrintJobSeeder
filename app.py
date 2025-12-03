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
    return render_template('index.html', presets=INDUSTRY_PRESETS, username_presets=USERNAME_PRESETS)


@app.route('/api/presets', methods=['GET'])
def get_presets():
    """Return industry presets as JSON"""
    return jsonify({'filenames': INDUSTRY_PRESETS, 'usernames': USERNAME_PRESETS})


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
