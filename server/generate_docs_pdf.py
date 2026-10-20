import sys
import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

class ForensicDocPDF(FPDF):
    def header(self):
        self.set_fill_color(24, 28, 36)
        self.rect(0, 0, 210, 14, 'F')
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(200, 210, 225)
        self.set_xy(10, 3)
        self.cell(100, 8, 'DECECS CORE -- DIGITAL EVIDENCE & CYBER FORENSICS WORKSTATION', new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(160, 175, 200)
        self.cell(90, 8, 'CLASSIFICATION: LAW ENFORCEMENT SENSITIVE // STRICT CUSTODY', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')
        self.ln(6)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(200, 210, 225)
        self.set_line_width(0.2)
        self.line(10, 283, 200, 283)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(120, 130, 145)
        self.cell(90, 8, 'ISO/IEC 27037 & NIST SP 800-86 Compliant Architecture', new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(100, 8, f'Page {self.page_no()} of {{nb}}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')

    def chapter_title(self, num, label):
        self.set_fill_color(230, 238, 248)
        self.set_draw_color(30, 64, 175)
        self.set_line_width(0.5)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(15, 23, 42)
        self.cell(0, 7, f'  {num}. {label.upper()}', border='L', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def section_title(self, label):
        self.set_font('Helvetica', 'B', 9.5)
        self.set_text_color(30, 58, 138)
        self.cell(0, 5.5, label, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def body_text(self, text):
        self.set_font('Helvetica', '', 8.5)
        self.set_text_color(30, 41, 59)
        self.multi_cell(0, 4.2, text)
        self.ln(2)

    def bullet_point(self, title, desc):
        self.set_font('Helvetica', 'B', 8.5)
        self.set_text_color(15, 23, 42)
        self.cell(5, 4.2, '-', new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(46, 4.2, f'{title}: ', new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font('Helvetica', '', 8.5)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 4.2, desc)
        self.ln(1)

    def key_value_box(self, items):
        self.set_fill_color(248, 250, 252)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)
        box_height = len(items) * 5 + 4
        self.rect(self.get_x(), self.get_y(), 190, box_height, 'DF')
        self.set_xy(self.get_x() + 2, self.get_y() + 2)
        for k, v in items:
            self.set_font('Helvetica', 'B', 8)
            self.set_text_color(71, 85, 105)
            self.cell(48, 4.8, k, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_font('Helvetica', '', 8)
            self.set_text_color(15, 23, 42)
            self.cell(138, 4.8, str(v), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_x(self.get_x() + 2)
        self.ln(3)

def generate_full_pdf(output_path):
    pdf = ForensicDocPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(10, 18, 10)

    # ------------------ COVER PAGE ------------------
    pdf.add_page()
    pdf.ln(10)
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(10, 25, 190, 44, 'F')
    
    pdf.set_xy(15, 30)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(180, 8, 'DECECS CORE FORENSIC PLATFORM', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_xy(15, 40)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(180, 5, 'Digital Evidence Collection, Extraction, Custody & Security Workstation', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(15, 47)
    pdf.set_font('Helvetica', 'I', 8.5)
    pdf.set_text_color(56, 189, 248)
    pdf.cell(180, 5, 'Complete System Architecture, Feature Modules, and End-to-End Workflows', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(74)
    pdf.section_title('SYSTEM METADATA & DOCUMENT CONTROL')
    doc_info = [
        ('Document Version', 'v1.0.0-PROD (Complete In-and-Out Feature & Workflow Specification)'),
        ('Classification Level', 'INTERNAL // LAW ENFORCEMENT & FORENSIC TEAMS ONLY'),
        ('Compliance Standards', 'ISO/IEC 27037 (Digital Evidence Handling), NIST SP 800-86, FIPS 140-3'),
        ('Backend Architecture', 'FastAPI (Python 3.11) Async Engine + MongoDB Motor Driver + JWT / ESP32 MFA'),
        ('Frontend Architecture', 'React 18 + TypeScript + Vite + Tailwind / Forensic Design Tokens'),
        ('Cryptographic Standard', 'SHA-256, MD5, HMAC-SHA256, BCrypt (Cost 12), Hardware Token Challenge'),
        ('AI Analytics Engine', 'Google Gemini Pro / Local LLM Multi-Modal Forensic Extraction Pipeline'),
        ('Target Environment', 'Forensic Laboratories, SOC/CERT Incident Response, Judicial Law Enforcement')
    ]
    pdf.key_value_box(doc_info)

    pdf.section_title('EXECUTIVE OVERVIEW')
    pdf.body_text(
        'DECECS CORE is an enterprise-grade Digital Forensics and Incident Response (DFIR) workstation and evidence '
        'management system. It provides end-to-end chain of custody tracking, forensic file extraction, automated '
        'indicator of compromise (IOC) parsing, knowledge graph correlation, AI-assisted pattern analysis, and court-admissible '
        'audit documentation. Built to withstand judicial scrutiny, every single data point is cryptographically sealed and tracked.'
    )
    
    # ------------------ TABLE OF CONTENTS ------------------
    pdf.ln(2)
    pdf.section_title('DOCUMENT MODULE INDEX')
    modules = [
        ('Module 1', 'Dual-Layer Authentication & Hardware ESP32 Token Security'),
        ('Module 2', 'Case Lifecycle Management & Multi-Investigator Assignment'),
        ('Module 3', 'Evidence Ingestion, Extraction & Cryptographic Vault (SHA-256/EXIF/IOC)'),
        ('Module 4', 'Cryptographic Chain of Custody & Court-Admissible Verifications'),
        ('Module 5', 'Multi-Dimensional Forensic Link Analysis & Knowledge Graph Engine'),
        ('Module 6', 'AI-Powered Deep Forensic Analysis & Threat Intelligence Pipeline'),
        ('Module 7', 'Risk Matrix, Vulnerability Scoring & Threat Analytics Engine'),
        ('Module 8', 'Unified Multi-Source Forensic Timeline Chronology'),
        ('Module 9', 'Real-Time SOC Security Monitoring, Audit Logs & Intrusion Alerts'),
        ('Module 10', 'Automated Forensic Audit Reports & Case Docket Export'),
        ('Module 11', 'Vault Backup, Snapshot Recovery & System Administration')
    ]
    for m_id, m_name in modules:
        pdf.bullet_point(m_id, m_name)

    # ------------------ MODULE 1 ------------------
    pdf.add_page()
    pdf.chapter_title('1', 'Dual-Layer Authentication & Hardware ESP32 MFA')
    pdf.body_text(
        'DECECS CORE implements high-assurance identity verification to prevent unauthorized access to judicial digital evidence. '
        'The authentication architecture supports standard cryptographic credentials combined with physical hardware token validation.'
    )
    pdf.section_title('1.1 Workflow & Sequence of Operations')
    pdf.bullet_point('Credential Submission', 'Investigator submits username/badge ID and password via client interface.')
    pdf.bullet_point('Password Hash Verification', 'FastAPI server validates against MongoDB using BCrypt with salt rounds = 12.')
    pdf.bullet_point('Hardware ESP32 Validation', 'Physical ESP32 / YubiKey hardware token sends a unique hardware serial and HMAC challenge signature via USB/Serial or hardware webhook.')
    pdf.bullet_point('JWT Issuance', 'Upon mutual verification, the server issues a cryptographically signed JWT with claims: user ID, full name, assigned role, and token expiry (default 8 hours).')
    pdf.bullet_point('Role-Based Access Control', 'Enforces strict clearance levels across 4 roles: Lead Investigator, Forensic Analyst, Evidence Custodian, and System Admin.')
    pdf.bullet_point('Immutable Session Audit', 'Every login success, failure, IP address, and user-agent is committed to the immutable audit database.')

    pdf.ln(2)
    # ------------------ MODULE 2 ------------------
    pdf.chapter_title('2', 'Case Lifecycle Management & Assignment')
    pdf.body_text(
        'The Case Management module serves as the master folder for all investigative procedures, tying evidence, notes, suspects, '
        'and timelines into a unified judicial dossier.'
    )
    pdf.section_title('2.1 Core Capabilities & Status State Machine')
    pdf.bullet_point('Case Identification', 'Automated sequential generation of unique Case IDs (e.g., CAS-2026-001, CR-9842).')
    pdf.bullet_point('Status States', 'Strict state transitions: OPEN -> ACTIVE_INVESTIGATION -> UNDER_REVIEW -> CLOSED -> ARCHIVED.')
    pdf.bullet_point('Severity Ratings', 'Configurable priority scoring: CRITICAL, HIGH, MEDIUM, LOW with visual triage alerts.')
    pdf.bullet_point('Team Collaboration', 'Assignment of Primary Lead Investigator and secondary analysts with granular view/edit permissions.')
    pdf.bullet_point('Dossier Summary', 'Real-time roll-up metrics: Total Evidence Items, Verified Hashes, IOC count, and Risk Score.')

    pdf.ln(2)
    # ------------------ MODULE 3 ------------------
    pdf.chapter_title('3', 'Evidence Ingestion, Extraction & Cryptographic Vault')
    pdf.body_text(
        'The Evidence Vault is the core storage and analysis engine. It ensures bit-stream integrity adherence '
        'following ISO/IEC 27037 standards from the moment evidence enters the laboratory.'
    )
    pdf.section_title('3.1 Ingestion & Processing Pipeline')
    pdf.bullet_point('Write-Blocking Protocol', 'Files are ingested read-only; physical file bytes are stored with restricted POSIX permissions.')
    pdf.bullet_point('Dual-Hash Fingerprinting', 'Simultaneous generation of SHA-256 and MD5 cryptographic hashes upon arrival.')
    pdf.bullet_point('Automated EXIF & GPS Parser', 'Extracts camera make/model, ISO, aperture, software version, and embedded GPS coordinates (latitude/longitude) with reverse geocoding.')
    pdf.bullet_point('Automated IOC Extractor', 'RegEx and heuristic extraction of IPv4/IPv6 addresses, domains, suspicious URLs, email addresses, and MD5/SHA256 malware signatures from memory dumps and log files.')
    pdf.bullet_point('Metadata Normalization', 'Captures file size, MIME type, MAC times (Modified, Accessed, Created), and device hardware serials.')
    pdf.bullet_point('Integrity Re-Verification', 'One-click automated hashing verification to detect bit-rot or illicit evidence tampering.')

    # ------------------ MODULE 4 ------------------
    pdf.add_page()
    pdf.chapter_title('4', 'Cryptographic Chain of Custody')
    pdf.body_text(
        'The Chain of Custody is legally required for evidence admissibility in court. DECECS CORE enforces a '
        'blockchain-like sequential verification ledger.'
    )
    pdf.section_title('4.1 Chain Actions & Cryptographic Sealing')
    pdf.bullet_point('Tracked Operations', 'CHECK_IN, CHECK_OUT, FORENSIC_ACQUISITION, LABORATORY_ANALYSIS, COURT_SUBMISSION, TRANSFER, DISPOSAL.')
    pdf.bullet_point('Custody Record Schema', 'Each transfer logs: Timestamp, Originating Custodian, Receiving Custodian, Purpose, Location/Vault ID, and SHA-256 validation status.')
    pdf.bullet_point('Immutable Sequence', 'Previous entry hash is linked to subsequent actions, preventing database tampering or backdating.')
    pdf.bullet_point('Integrity Verification Badge', 'Visual green/red audit badge on UI confirming if the evidence chain remains uncompromised.')

    pdf.ln(2)
    # ------------------ MODULE 5 ------------------
    pdf.chapter_title('5', 'Forensic Link Analysis & Knowledge Graph Engine')
    pdf.body_text(
        'The Knowledge Graph transforms unstructured case evidence into an interactive relationship network, '
        'revealing hidden links between suspects, devices, IP addresses, domains, and incident events.'
    )
    pdf.section_title('5.1 Graph Architecture & Visualization')
    pdf.bullet_point('Node Classification', 'Color-coded nodes: Case (Blue), Evidence File (Cyan), Suspect/Actor (Orange), Network IOC/IP (Red), Domain (Purple), Location/GPS (Emerald).')
    pdf.bullet_point('Edge Semantic Types', 'Explicit relationships: "ORIGINATED_FROM", "COMMUNICATED_WITH", "EXTRACTED_FROM", "LOCATED_AT", "CONTROLLED_BY".')
    pdf.bullet_point('Interactive Controls', 'Force-directed simulation physics, zoom/pan canvas, node search, filter by entity type, depth expansion, and degree centrality calculation.')
    pdf.bullet_point('Forensic Inspector Panel', 'Clicking any entity reveals raw metadata, linked cases, hash status, and connected artifact summaries.')

    pdf.ln(2)
    # ------------------ MODULE 6 ------------------
    pdf.chapter_title('6', 'AI-Powered Deep Forensic Analysis Engine')
    pdf.body_text(
        'Integrating advanced LLM intelligence (Google Gemini / Local Multimodal LLMs), this module accelerates triage '
        'by scanning thousands of lines of logs, emails, and device dumps in seconds.'
    )
    pdf.section_title('6.1 AI Capabilities & Analysis Modes')
    pdf.bullet_point('Automated Executive Synthesis', 'Generates judicial-ready summaries explaining what happened, how evidence was compromised, and key findings.')
    pdf.bullet_point('Behavioral Threat Profiling', 'Identifies attacker TTPs (Tactics, Techniques, and Procedures) mapped to MITRE ATT&CK framework.')
    pdf.bullet_point('Cross-Evidence Correlation', 'Detects matching IP addresses, encryption keys, or communication patterns across separate evidence files.')
    pdf.bullet_point('Interactive Forensic Copilot', 'Natural language Q&A over the active case corpus (e.g., "Show all IP addresses that connected between 02:00 and 04:00 UTC").')
    pdf.bullet_point('Confidence & Hallucination Guard', 'Every AI statement is cited with exact evidence artifact IDs and byte offsets.')

    # ------------------ MODULE 7 & 8 ------------------
    pdf.add_page()
    pdf.chapter_title('7', 'Risk Matrix & Threat Analytics Engine')
    pdf.body_text(
        'DECECS CORE automatically computes dynamic risk scores for every case and evidence item based on '
        'multi-factor threat modeling.'
    )
    pdf.section_title('7.1 Risk Scoring Formula & Factors')
    pdf.bullet_point('Tamper Risk Index', 'Evaluates hash mismatch history, transfer frequency, and unverified custody periods.')
    pdf.bullet_point('IOC Threat Density', 'Weighs known malicious IP reputation, CVE severity, and malware family indicators.')
    pdf.bullet_point('Case Complexity Matrix', 'Multi-variant calculation incorporating evidence count, suspect count, cross-jurisdiction tags, and exposure level.')
    pdf.bullet_point('Real-Time Gauge Visualization', 'Color-coded risk dials (0-100) with breakdown of primary risk contributors.')

    pdf.ln(2)
    pdf.chapter_title('8', 'Unified Forensic Timeline Chronology')
    pdf.body_text(
        'Chronological sequencing is vital for establishing motive, opportunity, and timeline of cyber attacks. '
        'DECECS aggregates event sources into a unified, high-precision timeline.'
    )
    pdf.section_title('8.1 Event Aggregation & Multi-Source Synthesis')
    pdf.bullet_point('File System Timelines', 'Normalized Modified, Accessed, Created, and Changed (MACC) timestamps.')
    pdf.bullet_point('EXIF Capture Timestamps', 'Hardware photo/video capture timestamps adjusted for local timezone offset.')
    pdf.bullet_point('Network & Syslog Events', 'Web server access logs, firewall connection attempts, and authentication records.')
    pdf.bullet_point('Custody Milestones', 'Timestamped physical evidence movements and forensic acquisition checkpoints.')
    pdf.bullet_point('Chronological Filter & Search', 'Filter by date range, event severity, source evidence item, or keyword.')

    # ------------------ MODULE 9 & 10 & 11 ------------------
    pdf.add_page()
    pdf.chapter_title('9', 'SOC Security Monitoring, Audit Logs & Intrusion Alerts')
    pdf.body_text(
        'Continuous surveillance of platform access ensures that forensic integrity is never compromised from internal or external threats.'
    )
    pdf.section_title('9.1 Alerting & Detection Logic')
    pdf.bullet_point('Brute Force Detection', 'Triggers alert on repeated failed login attempts from specific IPs or accounts.')
    pdf.bullet_point('Hardware Token Disconnect Alarms', 'Immediate security broadcast if an investigator active session loses ESP32 hardware handshake.')
    pdf.bullet_point('Evidence Tamper Alarm', 'Instant critical notification if background hash verification detects a mismatch.')
    pdf.bullet_point('SOC Triage Dashboard', 'Acknowledge, escalate, or resolve alerts with investigator notes and timestamps.')

    pdf.ln(2)
    pdf.chapter_title('10', 'Court-Admissible Reports & Case Docket Export')
    pdf.body_text(
        'One-click export of comprehensive judicial dockets formatted according to international forensic reporting standards.'
    )
    pdf.section_title('10.1 Report Sections & Compliance')
    pdf.bullet_point('Formal Cover Page', 'Case number, jurisdiction, lead investigator badge, and official agency insignia.')
    pdf.bullet_point('Evidence Manifest', 'Tabular ledger of all items with filename, type, file size, SHA-256 hash, and MD5 hash.')
    pdf.bullet_point('Custody Ledger', 'Full chronological custody trail with timestamps, names, and transfer authorizations.')
    pdf.bullet_point('Forensic Findings & AI Summary', 'Synthesized analytical findings, extracted IOCs, and analyst conclusions.')
    pdf.bullet_point('Digital Verification Seal', 'System-generated verification QR/Barcode and cryptographically signed summary hash.')

    pdf.ln(2)
    pdf.chapter_title('11', 'Vault Backup, Snapshot Recovery & Disaster Recovery')
    pdf.body_text(
        'Enterprise resilience protocols ensure that digital evidence is immune to hardware failure, database corruption, or ransomware.'
    )
    pdf.section_title('11.1 Backup Architecture')
    pdf.bullet_point('Automated Snapshots', 'Scheduled full database and evidence storage snapshots with gzip compression.')
    pdf.bullet_point('AES-256 Encryption', 'All backup archives are encrypted with secondary master keys before storage.')
    pdf.bullet_point('Point-in-Time Restoration', 'One-click restoration of historical cases and evidence states.')

    # Save PDF
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
    print(f'Successfully generated PDF at: {output_path}')

if __name__ == '__main__':
    target_path = sys.argv[1] if len(sys.argv) > 1 else r'c:\Users\Hari\Downloads\Macro\Macro\DECECS_CORE_System_Documentation.pdf'
    generate_full_pdf(target_path)
