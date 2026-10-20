import os
import hashlib
from datetime import datetime
from fpdf import FPDF
from app.core.config import settings

def _safe_text(s) -> str:
    """Sanitize strings to latin-1 compatible ASCII for core PDF fonts."""
    if s is None:
        return ""
    text = str(s)
    replacements = {
        "•": "*",
        "✓": "[PASS]",
        "✔": "[PASS]",
        "✗": "[FAIL]",
        "—": "-",
        "–": "-",
        '"': '"',
        '"': '"',
        "'": "'",
        "'": "'",
        "…": "...",
        "≥": ">=",
        "≤": "<=",
        "≠": "!=",
        "→": "->",
        "←": "<-",
        "™": "(TM)",
        "©": "(C)",
        "®": "(R)",
        "°": " deg",
        "µ": "u",
        "±": "+/-",
        "×": "x"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")

class DetailedWorkflowPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.alias_nb_pages()

    def header(self):
        if self.page_no() == 1:
            return  # Suppress running header on cover page
        self.set_font("helvetica", "B", 8)
        self.set_text_color(100, 116, 139) # Slate-500
        self.cell(120, 5, _safe_text("SECURE FORENSIC IoT PLATFORM (DECCS) // SYSTEM WORKFLOW & ARCHITECTURE"), border=0, align="L")
        self.cell(70, 5, "CONFIDENTIAL // TECHNICAL SPECIFICATION", border=0, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(203, 213, 225) # Slate-300
        self.set_line_width(0.3)
        self.line(10, 14, 200, 14)
        self.ln(5)

    def footer(self):
        if self.page_no() == 1:
            return  # Suppress running footer on cover page
        self.set_y(-14)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(148, 163, 184) # Slate-400
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)
        self.line(10, self.get_y() - 2, 200, self.get_y() - 2)
        self.cell(100, 8, _safe_text("AI-Powered Secure Digital Evidence Collection & Analysis System"), border=0, align="L")
        self.cell(90, 8, f"Page {self.page_no()} of {{nb}}", border=0, align="R")

    # Helper UI primitives
    def draw_section_heading(self, number: str, title: str):
        self.ln(4)
        # Accent left bar
        y = self.get_y()
        self.set_fill_color(37, 99, 235) # Blue-600
        self.rect(10, y, 3.5, 7, style="F")
        self.set_x(15)
        self.set_font("helvetica", "B", 13)
        self.set_text_color(15, 23, 42) # Slate-900
        self.cell(0, 7, _safe_text(f"{number}. {title}"), border=0, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def draw_sub_heading(self, subtitle: str):
        self.set_font("helvetica", "B", 10.5)
        self.set_text_color(30, 41, 59) # Slate-800
        self.cell(0, 6, _safe_text(subtitle), border=0, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def draw_paragraph(self, text: str, ln: float = 2):
        self.set_font("helvetica", "", 9)
        self.set_text_color(51, 65, 85) # Slate-700
        self.multi_cell(0, 4.8, _safe_text(text))
        self.ln(ln)

    def draw_callout(self, title: str, body: str, box_type: str = "info"):
        y = self.get_y()
        if box_type == "warning":
            bg = (254, 242, 242)
            border = (239, 68, 68)
            tcolor = (153, 27, 27)
        elif box_type == "success":
            bg = (240, 253, 244)
            border = (34, 197, 94)
            tcolor = (20, 83, 45)
        else: # info
            bg = (239, 246, 255)
            border = (59, 130, 246)
            tcolor = (30, 58, 138)

        self.set_fill_color(*bg)
        self.set_draw_color(*border)
        self.set_line_width(0.4)

        # Estimate height
        temp_y = self.get_y()
        self.set_font("helvetica", "B", 8.5)
        # 10 mm margin left/right
        w = 190
        # Draw box
        self.rect(10, temp_y, w, 15, style="DF")
        self.set_xy(14, temp_y + 2)
        self.set_text_color(*tcolor)
        self.cell(0, 4.5, _safe_text(f"[{title.upper()}]"), border=0, new_x="LMARGIN", new_y="NEXT")
        self.set_x(14)
        self.set_font("helvetica", "", 8.5)
        self.set_text_color(51, 65, 85)
        self.multi_cell(182, 4.2, _safe_text(body))
        self.set_y(temp_y + 17)

    def draw_table_header(self, cols, widths):
        self.set_fill_color(241, 245, 249) # Slate-100
        self.set_draw_color(203, 213, 225) # Slate-300
        self.set_line_width(0.2)
        self.set_font("helvetica", "B", 8)
        self.set_text_color(15, 23, 42)
        for i, col in enumerate(cols):
            self.cell(widths[i], 6, _safe_text(col), border=1, align="C", fill=True)
        self.ln(6)

    def draw_table_row(self, row, widths, is_even=False, align_list=None):
        if is_even:
            self.set_fill_color(248, 250, 252)
        else:
            self.set_fill_color(255, 255, 255)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.15)
        self.set_font("helvetica", "", 7.8)
        self.set_text_color(51, 65, 85)
        for i, val in enumerate(row):
            al = align_list[i] if align_list and i < len(align_list) else "L"
            self.cell(widths[i], 5.2, _safe_text(val), border=1, align=al, fill=True)
        self.ln(5.2)

def generate_pdf(output_path: str):
    pdf = DetailedWorkflowPDF()

    # ==========================================
    # PAGE 1: COVER PAGE
    # ==========================================
    pdf.add_page()
    
    # Top banner decorative gradient box
    pdf.set_fill_color(15, 23, 42) # Slate-900
    pdf.rect(0, 0, 210, 85, style="F")

    # Blue accent stripe
    pdf.set_fill_color(37, 99, 235) # Blue-600
    pdf.rect(0, 85, 210, 4, style="F")

    # Cover Title
    pdf.set_xy(15, 22)
    pdf.set_font("helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, _safe_text("SECURE DIGITAL EVIDENCE COLLECTION"), border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(15)
    pdf.cell(0, 9, _safe_text("& ANALYSIS SYSTEM (DECCS)"), border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_x(15)
    pdf.set_font("helvetica", "", 12)
    pdf.set_text_color(148, 163, 184) # Slate-400
    pdf.cell(0, 7, _safe_text("AI-Powered Cyber-Forensic Ingestion Platform with IoT Hardware Integration"), border=0, new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(15, 54)
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(56, 189, 248) # Sky-400
    pdf.cell(0, 5, _safe_text("STANDARDS: ISO/IEC 27037 // NIST SP 800-86 // FIPS 180-4 SHA-256"), border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(15)
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(203, 213, 225)
    pdf.cell(0, 5, _safe_text("CLASSIFICATION: LAW ENFORCEMENT & FORENSIC LABORATORY TECHNICAL GUIDE"), border=0, new_x="LMARGIN", new_y="NEXT")

    # Document details block
    pdf.set_y(102)
    pdf.draw_section_heading("0", "EXECUTIVE DOCUMENT CONTROL")
    
    metadata = [
        ["Project Title", "AI-Powered Secure Digital Evidence Collection and Analysis System using IoT"],
        ["Platform Acronym", "DECCS (Digital Evidence Collection and Custody System)"],
        ["Document Type", "System Workflow, Architectural Blueprint & Operational Engineering Manual"],
        ["Target Audience", "Forensic Investigators, Systems Engineers, Cryptographic Auditors, Courts"],
        ["Release Version", "Version 2.4.0-Production Baseline (Stabilized Pre-Hardware & Simulation Verified)"],
        ["Cryptographic Primitives", "Streaming FIPS 180-4 SHA-256, HMAC-SHA256 JWT, Cryptographic Hash Chaining"],
        ["Compliance Benchmarks", "ISO/IEC 27037:2012 (DEIR/DEIE), NIST SP 800-86, Federal Rules of Evidence Rule 901"],
        ["Backend Core", "FastAPI (Python 3.11+), Motor AsyncIO, MongoDB 7.0, Pydantic v2 Models"],
        ["Frontend UI", "React 19, TypeScript, Tailwind CSS, Vite, Glassmorphic Forensic Dashboard"],
        ["Hardware Subsystem", "ESP32 SoC, MFRC522 RFID (13.56MHz), R307 Optical Fingerprint, SSD1306 OLED"],
        ["Publication Date", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")]
    ]
    
    col_w = [48, 142]
    pdf.draw_table_header(["METADATA FIELD", "SPECIFICATION / CONFIGURATION VALUE"], col_w)
    for i, row in enumerate(metadata):
        pdf.draw_table_row(row, col_w, is_even=(i%2==0))

    pdf.ln(6)
    pdf.draw_callout("Document Purpose & Scope", 
                     "This document provides the definitive, end-to-end technical explanation of how evidence, "
                     "biometric authentication, cryptographic integrity records, multi-source timeline events, "
                     "AI threat scoring, and court-admissible PDF reports flow through the DECCS architecture.", 
                     box_type="info")

    # ==========================================
    # PAGE 2: EXECUTIVE SUMMARY & ARCHITECTURE
    # ==========================================
    pdf.add_page()
    pdf.draw_section_heading("1", "EXECUTIVE SUMMARY & PROBLEM STATEMENT")
    
    pdf.draw_paragraph(
        "Digital forensics investigations face strict legal and technical challenges. In conventional "
        "evidence handling, digital artifacts are susceptible to unrecorded modifications, improper storage, "
        "and contested chain-of-custody logs. The lack of hardware-level physical identity verification and "
        "fragmented analysis tools often lead to evidence inadmissibility in judicial proceedings under "
        "Federal Rules of Evidence Rule 901 and ISO/IEC 27037."
    )
    pdf.draw_paragraph(
        "The Secure Digital Evidence Collection and Analysis System (DECCS) resolves these vulnerabilities "
        "by introducing a unified cyber-physical ecosystem combining: (1) Hardware-enforced 2FA using IoT "
        "(RFID card UID scan and optical biometric fingerprint verification), (2) Instantaneous streaming "
        "SHA-256 baseline hashing upon intake, (3) An immutable, append-only cryptographic chain-of-custody "
        "ledger, (4) An automated metadata and multi-source chronological timeline engine, (5) Deterministic "
        "graph intelligence with AI risk analysis, and (6) Digitally sealed, court-admissible PDF reports."
    )

    pdf.draw_section_heading("2", "SYSTEM ARCHITECTURE & LAYER TOPOLOGY")
    pdf.draw_paragraph(
        "The system operates on an asynchronous, decoupled 5-tier architecture ensuring complete fault "
        "isolation, cryptographic integrity, and horizontal scalability."
    )

    arch_layers = [
        ["1. IoT Hardware Layer", "ESP32 SoC + MFRC522 RFID + R307 Fingerprint sensor. Communicates via WebSocket & REST with heartbeat monitoring. Transmits physical custody telemetry."],
        ["2. Simulation Layer", "Full software simulation engine with toggleable modes. Allows comprehensive UI and automated test operations without requiring physical hardware connected."],
        ["3. Asynchronous Core", "FastAPI web framework with Python asyncio. Handles JWT authentication, RBAC authorization, streaming file ingestion, metadata extraction, and report compilation."],
        ["4. Storage & Ledger", "MongoDB document database (users, cases, evidence, custody, events, reports, devices) paired with a sandboxed, path-traversal-proof evidence file vault."],
        ["5. AI & Analytical", "Deterministic Risk Scoring Engine (0-100), Evidence Graph Topology builder, Google Gemini AI threat assessment with offline rule-based fallback."],
        ["6. Presentation UI", "React 19 + TypeScript single-page application styled with Tailwind CSS, featuring cyber-forensics dark theme, live canvas graph, and timeline filters."]
    ]
    pdf.draw_table_header(["SYSTEM LAYER", "RESPONSIBILITIES & ENGINEERING HIGHLIGHTS"], [45, 145])
    for i, row in enumerate(arch_layers):
        pdf.draw_table_row(row, [45, 145], is_even=(i%2==0))

    pdf.ln(4)
    pdf.draw_sub_heading("Visual Dataflow & Component Interaction Model")
    pdf.draw_paragraph(
        "Physical Device / Simulator -> [WebSocket/REST] -> Hardware Router -> Auth Dependency (RBAC) \n"
        "-> File Vault Streaming SHA-256 Ingestion -> Metadata Extraction Engine -> MongoDB Document Store \n"
        "-> Cryptographic Custody Ledger -> Multi-Source Timeline Engine -> Graph & AI Risk Scoring Engine \n"
        "-> PDF Compilation Engine -> Cryptographic Digital Seal (SHA-256) -> Verified Court Exhibit"
    )

    # ==========================================
    # PAGE 3: PHASE 0 - AUTH & HARDWARE 2FA
    # ==========================================
    pdf.add_page()
    pdf.draw_section_heading("3", "PHASE 0: HARDWARE-ENFORCED 2FA & NODE MANAGEMENT")

    pdf.draw_sub_heading("3.1 Biometric & RFID Two-Factor Ingestion")
    pdf.draw_paragraph(
        "In high-security forensic facilities, software credentials alone are insufficient to guarantee physical "
        "custody. DECCS enforces hardware-level identity bindings. Every investigator profile is linked to: "
        "(a) An RFID Card UID (e.g., '04A1B2C3') and (b) An Optical Fingerprint Template ID (e.g., ID 12)."
    )
    pdf.draw_paragraph(
        "When an officer presents evidence at an ingestion node, the ESP32 terminal reads the card and scans "
        "the fingerprint. The terminal transmits the payload to POST /api/hardware/authenticate with device ID, "
        "hardware timestamp, and credentials. The backend verifies the device status, matches the biometric signature, "
        "issues an ephemeral authentication grant, and broadcasts real-time telemetry over WebSocket."
    )

    pdf.draw_sub_heading("3.2 Hardware-Only Mode vs. Simulation Mode")
    pdf.draw_paragraph(
        "The system incorporates an institutional security toggle stored in the global settings collection:"
    )

    mode_table = [
        ["Feature / Policy", "Simulation Mode (Active)", "Hardware-Only Mode (Enforced)"],
        ["Password Login (/auth/login)", "Allowed (for dev, training & simulation)", "STRICTLY FORBIDDEN (HTTP 403)"],
        ["Hardware Endpoint (/hardware/auth)", "Active with simulator and physical nodes", "Exclusively required for access"],
        ["Physical Hardware Required", "No (Virtual card & fingerprint IDs)", "Yes (Registered ESP32 terminal)"],
        ["Rogue Device Rejection", "Active (Unknown Device ID -> HTTP 400)", "Active (Unknown Device ID -> HTTP 400)"],
        ["Invalid Card Rejection", "Active (Unregistered UID -> HTTP 401)", "Active (Unregistered UID -> HTTP 401)"]
    ]
    pdf.draw_table_header(["SECURITY POLICY", "SIMULATION MODE", "HARDWARE-ONLY MODE"], [55, 65, 70])
    for i, row in enumerate(mode_table[1:]):
        pdf.draw_table_row(row, [55, 65, 70], is_even=(i%2==0))

    pdf.ln(3)
    pdf.draw_sub_heading("3.3 IoT Terminal Heartbeat & Watchdog Service")
    pdf.draw_paragraph(
        "Every authorized ESP32 ingestion terminal emits periodic heartbeats to POST /api/hardware/heartbeat "
        "carrying its MAC address and firmware revision. A FastAPI background daemon continuously audits active "
        "terminals. If a terminal misses heartbeats beyond the configured threshold, its status transitions to "
        "'offline', preventing unauthorized offline physical tampering."
    )

    # ==========================================
    # PAGE 4: PHASE 1 & 2 - CASES, VAULT & INTEGRITY
    # ==========================================
    pdf.add_page()
    pdf.draw_section_heading("4", "PHASE 1: CASE REGISTRY & AUTOMATED METADATA EXTRACTION")

    pdf.draw_sub_heading("4.1 Case Registry & Numbering Schema")
    pdf.draw_paragraph(
        "Every investigation begins with an official case container. Cases are uniquely indexed with sequential, "
        "audit-proof identifiers adhering to the format: DF-YYYY-XXXXXX (e.g., DF-2026-000001). Cases track priority "
        "(LOW, MEDIUM, HIGH, CRITICAL), status (OPEN, UNDER_INVESTIGATION, CLOSED, ARCHIVED), primary investigator, "
        "and strict immutable timestamps."
    )

    pdf.draw_sub_heading("4.2 Automated Forensic Metadata Extraction")
    pdf.draw_paragraph(
        "Upon file intake, the Metadata Extraction Engine automatically parses evidence files based on MIME type:"
    )
    meta_features = [
        ["Images (JPEG, PNG, TIFF)", "EXIF parsing, camera make/model, ISO, focal length, GPS latitude/longitude/altitude coordinates, dimension resolution."],
        ["Structured Data (CSV, JSON)", "Header extraction, row/column cardinality, key schema inspection, sample payload extraction."],
        ["Compressed Archives (ZIP)", "Internal file manifest, compressed vs uncompressed ratios, embedded member timestamps."],
        ["Documents & Plaintext", "Character count, line count, encoding detection, preliminary keyword indexing."]
    ]
    pdf.draw_table_header(["FILE CATEGORY", "EXTRACTED FORENSIC METADATA ARTIFACTS"], [50, 140])
    for i, row in enumerate(meta_features):
        pdf.draw_table_row(row, [50, 140], is_even=(i%2==0))

    pdf.ln(4)
    pdf.draw_section_heading("5", "PHASE 2: EVIDENCE VAULT & STREAMING SHA-256 INTEGRITY")

    pdf.draw_sub_heading("5.1 Streaming Bit-Stream Hashing (FIPS 180-4)")
    pdf.draw_paragraph(
        "Evidence files (especially disk images, memory dumps, and CCTV captures) can span tens of gigabytes. "
        "To prevent server memory exhaustion, DECCS implements chunked streaming ingestion. Files are processed "
        "in 64KB chunks directly to disk while concurrently computing the baseline SHA-256 cryptographic digest. "
        "The resultant 64-character hexadecimal hash is immutably registered in the database."
    )

    pdf.draw_sub_heading("5.2 Cryptographic Chain of Custody Ledger")
    pdf.draw_paragraph(
        "In accordance with ISO/IEC 27037 standards, evidence must have an unbroken, cryptographically verifiable "
        "chain of custody. The system maintains an append-only collection where each entry documents: (1) Timestamp, "
        "(2) Custodian Actor ID & Email, (3) Action Taken (COLLECTED, ACCESSED, TRANSFERRED, ANALYZED, TAMPER_DETECTED), "
        "(4) Purpose / Case Justification, and (5) Current SHA-256 Hash Verification."
    )

    pdf.draw_sub_heading("5.3 Active Tamper Verification & Controlled Integrity Audits")
    pdf.draw_paragraph(
        "At any point in the investigation or courtroom presentation, investigators can trigger POST /api/evidence/{id}/verify. "
        "The system re-reads the physical file from disk, computes a fresh SHA-256 digest, and compares it against the initial baseline. "
        "If the hashes match exactly, the evidence is tagged [VERIFIED]. If a single bit differs, the status immediately "
        "flips to [TAMPERED], triggering an emergency forensic event and chain-of-custody tamper alert."
    )

    # ==========================================
    # PAGE 5: PHASE 3 & 4 - TIMELINE & AI GRAPH
    # ==========================================
    pdf.add_page()
    pdf.draw_section_heading("6", "PHASE 3: FORENSIC EVENT & MULTI-SOURCE TIMELINE ENGINE")

    pdf.draw_sub_heading("6.1 Multi-Source Chronological Correlation")
    pdf.draw_paragraph(
        "Fragmented timestamps represent one of the greatest obstacles in digital forensics. The DECCS Timeline "
        "Engine synthesizes data across five heterogeneous sources into a unified, chronological master event stream:"
    )
    timeline_sources = [
        ["1. Forensic Events", "Manual or automated analytical observations logged directly by certified investigators."],
        ["2. Evidence Ingestion", "Milestones capturing exact moments files were ingested into the secure vault."],
        ["3. Custody Transfers", "Audit trail records capturing handoffs, forensic extractions, and custodial changes."],
        ["4. File Metadata Timestamps", "Embedded file creation, camera capture, and filesystem modification timestamps."],
        ["5. System Audit Logs", "Platform administrative actions, user logins, and configuration changes."]
    ]
    pdf.draw_table_header(["EVENT SOURCE", "INTEGRATION & CHRONOLOGICAL SIGNIFICANCE"], [45, 145])
    for i, row in enumerate(timeline_sources):
        pdf.draw_table_row(row, [45, 145], is_even=(i%2==0))

    pdf.ln(3)
    pdf.draw_sub_heading("6.2 Timestamp Precision & Confidence Modeling")
    pdf.draw_paragraph(
        "Because timestamps originating from compromised machines or disparate timezones may vary in reliability, "
        "the timeline engine tags each event with a precision enum: (a) EXACT (reliable NTP/hardware synchronized), "
        "(b) APPROXIMATE (known within a bounded window), or (c) UNKNOWN (undetermined sequence). Events are also "
        "scored with confidence levels (0.0 to 1.0) and severity ratings (LOW, MEDIUM, HIGH, CRITICAL)."
    )

    pdf.draw_section_heading("7", "PHASE 4: EVIDENCE GRAPH & DETERMINISTIC AI RISK SCORING")

    pdf.draw_sub_heading("7.1 Interactive Evidence Graph Topology")
    pdf.draw_paragraph(
        "The Graph Service builds a mathematical directed graph G = (V, E) reflecting case relationships. "
        "Vertices represent Cases, Evidence Exhibits, Custodians, and Forensic Events. Edges represent semantic "
        "connections such as BELONGS_TO, EXTRACTED_FROM, HANDLED_BY, and CORRELATED_WITH. The frontend renders "
        "this topology on an interactive HTML5 canvas allowing visual inspection of evidence chains."
    )

    pdf.draw_sub_heading("7.2 Deterministic Forensic Risk Formula (0 to 100)")
    pdf.draw_paragraph(
        "To eliminate subjective bias, the Risk Scoring Engine computes case risk using a strict mathematical formula:"
    )
    pdf.draw_callout("Risk Calculation Formula", 
                     "Case Risk Score = Min(100, Tamper_Penalties (max 40) + Event_Severity_Weights (max 30) + "
                     "Custody_Failure_Weights (max 15) + Evidence_Volume_Factor (max 15))\n"
                     "- Any TAMPERED file immediately incurs 35 points.\n"
                     "- CRITICAL events add 15 points each; HIGH severity events add 8 points each.\n"
                     "- Scores >= 70 = HIGH RISK (RED); 35-69 = MEDIUM RISK (AMBER); < 35 = LOW RISK (GREEN).",
                     box_type="warning")

    pdf.draw_sub_heading("7.3 Dual-Mode AI Threat Analysis (Gemini + Offline Engine)")
    pdf.draw_paragraph(
        "The AI Service provides deep investigative insights. When an API key is configured, it invokes Google Gemini "
        "AI with a prompt engineered to strictly segregate verified facts from speculative interpretations. When offline, "
        "an intelligent heuristic expert system generates deterministic threat vectors and prioritized actionable recommendations."
    )

    # ==========================================
    # PAGE 6: PHASE 5 & REPRODUCIBILITY
    # ==========================================
    pdf.add_page()
    pdf.draw_section_heading("8", "PHASE 5: COURT-ADMISSIBLE REPORT GENERATION & DIGITAL SEALS")

    pdf.draw_sub_heading("8.1 PDF Compilation & Judicial Admissibility")
    pdf.draw_paragraph(
        "The Report Engine compiles a comprehensive, multi-page legal document for each case. The document includes "
        "official case headers, an executive summary, evidence exhibit tables with full SHA-256 digests, integrity verification "
        "history, chronological timeline summaries, and chain-of-custody transfer logs. The layout strictly adheres "
        "to legal reporting standards for expert witness submission."
    )

    pdf.draw_sub_heading("8.2 Cryptographic Digital Sealing")
    pdf.draw_paragraph(
        "Upon generating the PDF binary, the system computes the SHA-256 hash of the complete byte stream before saving "
        "it to disk. This seal is registered in the forensic_reports collection alongside generation timestamps, version numbers, "
        "and compiler credentials. Anyone receiving the PDF can re-verify its cryptographic seal via GET /api/reports/{id}/verify, "
        "guaranteeing that the report itself has never been altered after issuance."
    )

    pdf.draw_section_heading("9", "SECURITY, AUDIT & FORENSIC STANDARDS COMPLIANCE")

    standards = [
        ["ISO/IEC 27037:2012", "Guidelines for identification, collection, acquisition, and preservation of digital evidence. DECCS enforces strict custody logging, immediate write-blocking logic, and bit-stream verification."],
        ["NIST SP 800-86", "Integration of forensic techniques into incident response. Automated metadata extraction, unified timeline correlation, and reproducible forensic methodologies."],
        ["FIPS 180-4 (SHA-256)", "Federal Information Processing Standard for Secure Hash Algorithms. Applied uniformly to evidence files, custody ledger transactions, and court-admissible PDF reports."],
        ["Path Traversal Defense", "All evidence file storage paths are validated against canonical path resolutions (os.path.realpath) preventing directory traversal (../) exploits."],
        ["Role-Based Access Control", "Granular role enforcement: 'admin' (full system control), 'investigator' (case and evidence handling), 'readonly' (court auditor view-only access)."]
    ]
    pdf.draw_table_header(["STANDARD / PRINCIPLE", "DECCS IMPLEMENTATION & DEFENSE MECHANISM"], [48, 142])
    for i, row in enumerate(standards):
        pdf.draw_table_row(row, [48, 142], is_even=(i%2==0))

    pdf.ln(4)
    pdf.draw_sub_heading("9.1 Immutable Audit Log System")
    pdf.draw_paragraph(
        "All system interactions (user authentication, permission modifications, evidence uploads, integrity verifications, "
        "and setting changes) are captured in the immutable audit_logs collection with IP addresses, user emails, "
        "action descriptors, and high-precision UTC timestamps. Audit logs cannot be modified or deleted via API."
    )

    # ==========================================
    # PAGE 7: REST API DIRECTORY & REFERENCE
    # ==========================================
    pdf.add_page()
    pdf.draw_section_heading("10", "COMPLETE REST API & WEBSOCKET DIRECTORY")
    pdf.draw_paragraph(
        "The DECCS backend exposes 37 secure REST endpoints and a real-time WebSocket interface documented below:"
    )

    api_routes = [
        ["POST", "/api/auth/login", "Authenticate via standard email/password (Simulation mode only)"],
        ["GET", "/api/auth/me", "Retrieve authenticated user identity, role, and biometric bindings"],
        ["POST", "/api/hardware/heartbeat", "IoT terminal ping emitting MAC address and firmware version"],
        ["POST", "/api/hardware/authenticate", "Hardware 2FA ingestion endpoint (RFID UID + Fingerprint ID)"],
        ["GET", "/api/hardware/devices", "List all registered IoT ingestion terminals and online status"],
        ["GET", "/api/cases", "Paginated case registry search with status and priority filtering"],
        ["POST", "/api/cases", "Create new forensic case container (allocates DF-YYYY-XXXXXX)"],
        ["GET", "/api/cases/{id}", "Fetch complete case details, metrics, and assigned investigators"],
        ["PATCH", "/api/cases/{id}", "Update case metadata, status, priority, or investigator assignments"],
        ["POST", "/api/evidence/upload", "Streaming evidence ingestion, 64KB SHA-256 calculation & vault storage"],
        ["GET", "/api/evidence", "Query evidence exhibits filtered by case, MIME type, or integrity status"],
        ["POST", "/api/evidence/{id}/verify", "Recalculate live SHA-256 against baseline digest (Tamper detection)"],
        ["POST", "/api/evidence/{id}/custody", "Append new custodial transfer or analysis record to chain-of-custody"],
        ["GET", "/api/evidence/{id}/custody", "Fetch unbroken chronological chain-of-custody ledger for exhibit"],
        ["GET", "/api/timeline/{case_id}", "Synthesized multi-source chronological timeline with server-side filters"],
        ["POST", "/api/events", "Record standalone forensic observation or critical incident milestone"],
        ["GET", "/api/graph/{case_id}", "Construct directed topological graph nodes and edges for visual canvas"],
        ["GET", "/api/risk/case/{id}", "Execute deterministic 0-100 forensic risk assessment formula"],
        ["POST", "/api/ai/analyze-threats/{case_id}", "Execute dual-mode AI threat analysis (Gemini or offline rules)"],
        ["POST", "/api/reports/generate/{case_id}", "Compile court-admissible PDF report and register SHA-256 digital seal"],
        ["GET", "/api/reports/{id}/download", "Securely download compiled PDF court report with path sanitization"],
        ["GET", "/api/settings", "Fetch system operational parameters and simulation toggle status"],
        ["POST", "/api/settings", "Update simulation mode or AI API configuration keys (Admin only)"],
        ["GET", "/api/audit-logs", "Query immutable administrative and operational event audit trail"],
        ["WS", "/ws/hardware", "Bi-directional WebSocket for real-time ESP32 hardware telemetry & alerts"]
    ]

    pdf.draw_table_header(["VERB", "ENDPOINT ROUTE", "FUNCTIONAL DESCRIPTION"], [18, 62, 110])
    for i, row in enumerate(api_routes):
        pdf.draw_table_row(row, [18, 62, 110], is_even=(i%2==0), align_list=["C", "L", "L"])

    # ==========================================
    # PAGE 8: OPERATIONAL RUNBOOK & SIMULATION GUIDE
    # ==========================================
    pdf.add_page()
    pdf.draw_section_heading("11", "OPERATIONAL RUNBOOK & SIMULATION GUIDE")

    pdf.draw_sub_heading("11.1 Zero-Hardware Operational Execution (Simulation Mode)")
    pdf.draw_paragraph(
        "To enable full functional testing, development, and demonstrations without physical ESP32 boards, "
        "the platform provides complete simulation capabilities. Follow this step-by-step workflow:"
    )

    steps = [
        ["Step 1: Start Services", "Backend: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000\nFrontend: npm run dev in client directory (http://localhost:5173)."],
        ["Step 2: Authenticate", "Log in as Lead Investigator (admin@forensics.gov / password123) or use the Hardware Simulation card in the UI header to simulate RFID 04A1B2C3 + Fingerprint 12."],
        ["Step 3: Register Case", "Navigate to 'Cases' -> 'New Case'. Provide Title, Description, and Priority. System allocates next sequence number DF-2026-XXXXXX."],
        ["Step 4: Ingest Evidence", "Open Case Detail -> Evidence Vault tab. Drag and drop file (image, document, zip). System calculates SHA-256 digest and extracts metadata."],
        ["Step 5: Custody & Integrity", "Trigger an on-demand integrity audit by clicking 'Verify Integrity'. System re-hashes the file and displays [PASS - 0 BIT DRIFT]."],
        ["Step 6: Timeline & Graph", "Review the synthesized chronological stream in 'Forensic Timeline' and inspect connected relationships in the 'Evidence Graph' canvas."],
        ["Step 7: AI Risk Assessment", "Navigate to 'AI Risk & Recommendations'. Click 'Run Analysis' to view deterministic score (0-100), threat vectors, and investigative actions."],
        ["Step 8: Court Report", "Navigate to 'Court Reports'. Click 'Generate Report'. Download the sealed PDF and verify its SHA-256 digital seal."]
    ]
    pdf.draw_table_header(["PHASE / STAGE", "EXACT STEP-BY-STEP OPERATIONAL INSTRUCTIONS"], [45, 145])
    for i, row in enumerate(steps):
        pdf.draw_table_row(row, [45, 145], is_even=(i%2==0))

    pdf.ln(4)
    pdf.draw_sub_heading("11.2 Default System Credentials (Post-Flush Baseline)")
    default_creds = [
        ["admin@forensics.gov", "password123", "Admin", "04A1B2C3", "12", "Chief Investigator - Full System Administration"],
        ["investigator@forensics.gov", "password123", "Investigator", "B1C2D3E4", "15", "Forensic Analyst - Evidence & Case Handling"],
        ["viewer@forensics.gov", "password123", "Read-Only", "N/A", "N/A", "Court Auditor - Read-Only Verification Access"]
    ]
    pdf.draw_table_header(["EMAIL", "PASSWORD", "ROLE", "RFID", "FP ID", "PERMISSIONS"], [45, 25, 24, 20, 16, 60])
    for i, row in enumerate(default_creds):
        pdf.draw_table_row(row, [45, 25, 24, 20, 16, 60], is_even=(i%2==0), align_list=["L", "C", "C", "C", "C", "L"])

    pdf.ln(5)
    pdf.draw_callout("Security Notice", 
                     "All test data has been cleanly flushed. The database and storage directories are in pristine "
                     "baseline state. The default accounts listed above are immediately available for login.",
                     box_type="success")

    # Output file
    pdf.output(output_path)
    print(f"[+] Successfully generated detailed workflow PDF at: {output_path}")

if __name__ == "__main__":
    out_file = os.path.abspath(r"d:\Macro\Digital_Forensics_System_Workflow.pdf")
    generate_pdf(out_file)
    # Compute SHA-256
    hasher = hashlib.sha256()
    with open(out_file, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    file_hash = hasher.hexdigest()
    file_size = os.path.getsize(out_file)
    print(f"[+] File Size: {file_size:,} bytes")
    print(f"[+] Cryptographic SHA-256 Seal: {file_hash}")
