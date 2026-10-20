import os
import hashlib
from datetime import datetime
from fpdf import FPDF

def _safe_text(s) -> str:
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
        "→": "->",
        "←": "<-"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")

class EndUserGuidePDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.alias_nb_pages()

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("helvetica", "B", 8.5)
        self.set_text_color(71, 85, 105)
        self.cell(120, 5, _safe_text("SECURE FORENSIC EVIDENCE SYSTEM (DECCS) // END-USER HANDBOOK"), border=0, align="L")
        self.cell(70, 5, "SIMPLE USER GUIDE", border=0, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.3)
        self.line(10, 14, 200, 14)
        self.ln(5)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)
        self.line(10, self.get_y() - 2, 200, self.get_y() - 2)
        self.cell(100, 8, _safe_text("Forensic Evidence Collection Platform - End-User Workflow Guide"), border=0, align="L")
        self.cell(90, 8, f"Page {self.page_no()} of {{nb}}", border=0, align="R")

    def draw_step_header(self, step_num: str, title: str, subtitle: str):
        self.ln(3)
        y = self.get_y()
        self.set_fill_color(37, 99, 235) # Blue
        self.rect(10, y, 4, 10, style="F")
        self.set_x(16)
        self.set_font("helvetica", "B", 13)
        self.set_text_color(15, 23, 42)
        self.cell(0, 6, _safe_text(f"STEP {step_num}: {title.upper()}"), border=0, new_x="LMARGIN", new_y="NEXT")
        self.set_x(16)
        self.set_font("helvetica", "I", 8.5)
        self.set_text_color(100, 116, 139)
        self.cell(0, 4, _safe_text(subtitle), border=0, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def draw_text(self, text: str, ln: float = 2.5):
        self.set_font("helvetica", "", 9.2)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 5, _safe_text(text))
        self.ln(ln)

    def draw_highlight_box(self, title: str, items: list, box_color="blue"):
        y = self.get_y()
        if box_color == "green":
            bg = (240, 253, 244)
            border = (34, 197, 94)
            tcolor = (20, 83, 45)
        elif box_color == "amber":
            bg = (254, 252, 232)
            border = (234, 179, 8)
            tcolor = (133, 77, 14)
        else:
            bg = (239, 246, 255)
            border = (59, 130, 246)
            tcolor = (30, 58, 138)

        self.set_fill_color(*bg)
        self.set_draw_color(*border)
        self.set_line_width(0.3)

        box_h = 10 + len(items) * 5.5
        self.rect(10, y, 190, box_h, style="DF")
        self.set_xy(14, y + 2.5)
        self.set_font("helvetica", "B", 9)
        self.set_text_color(*tcolor)
        self.cell(0, 5, _safe_text(f"KEY TAKEAWAYS: {title.upper()}"), border=0, new_x="LMARGIN", new_y="NEXT")
        
        for item in items:
            self.set_x(16)
            self.set_font("helvetica", "", 8.5)
            self.set_text_color(51, 65, 85)
            self.cell(0, 5, _safe_text(f"[+] {item}"), border=0, new_x="LMARGIN", new_y="NEXT")
        self.set_y(y + box_h + 3)

def generate_end_user_pdf(output_path: str):
    pdf = EndUserGuidePDF()

    # ============================================================
    # PAGE 1: COVER & WHAT IS THIS SYSTEM?
    # ============================================================
    pdf.add_page()
    
    # Hero banner
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 80, style="F")
    pdf.set_fill_color(37, 99, 235)
    pdf.rect(0, 80, 210, 4, style="F")

    pdf.set_xy(15, 20)
    pdf.set_font("helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, _safe_text("SECURE DIGITAL FORENSICS PLATFORM"), border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(15)
    pdf.cell(0, 9, _safe_text("COMPLETE END-USER WORKFLOW GUIDE"), border=0, new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(15)
    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 7, _safe_text("A Clear, Non-Technical Walkthrough for Investigators, Officers & Auditors"), border=0, new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(15, 52)
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(56, 189, 248)
    pdf.cell(0, 5, _safe_text("AUDIENCE: FORENSIC ANALYSTS // POLICE OFFICERS // LAWYERS // JUDGES"), border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(15)
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(203, 213, 225)
    pdf.cell(0, 5, _safe_text("PURPOSE: EXPLAINING HOW DIGITAL EVIDENCE IS COLLECTED, SECURED, AND PRESENTED"), border=0, new_x="LMARGIN", new_y="NEXT")

    # Introduction
    pdf.set_y(95)
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 7, _safe_text("WHAT IS THIS SYSTEM AND WHY DOES IT EXIST?"), border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.draw_text(
        "Imagine a crime or security incident takes place. Investigators recover laptops, smartphones, flash drives, "
        "and security camera recordings. In the past, someone could copy a file, accidentally alter its date, or even "
        "deliberately tamper with it before it reached a courtroom. If that happens, the judge will reject the evidence."
    )
    pdf.draw_text(
        "This system (DECCS - Digital Evidence Collection and Custody System) acts as an untamperable digital bank vault. "
        "From the exact second a piece of evidence arrives at the forensic laboratory to the moment it is printed out as "
        "a court report, every single touch, scan, and file modification is permanently recorded. Nobody can delete records, "
        "and nobody can tamper with evidence without immediately sounding an alarm."
    )

    pdf.draw_highlight_box("Who Uses This System?", [
        "Chief Investigators / Administrators: Oversee all active cases, assign personnel, and audit security.",
        "Forensic Investigators & Police: Deposit seized files, inspect hidden camera/phone data, and log incident events.",
        "Judges, Prosecutors & Auditors: Review certified reports, inspect custody histories, and verify digital seals."
    ], box_color="blue")

    # ============================================================
    # PAGE 2: STEPS 1 & 2 (LOGIN & CASE CREATION)
    # ============================================================
    pdf.add_page()
    
    pdf.draw_step_header("1", "Secure Check-In (Two-Factor Biometric Login)", "How authorized officers enter the system")
    pdf.draw_text(
        "To prevent unauthorized people from accessing sensitive police files, the system does not just rely on simple "
        "passwords. In a real forensic room, there is an IoT terminal (equipped with an ESP32 microchip, a card reader, and "
        "a fingerprint scanner)."
    )
    pdf.draw_text(
        "How it works for the investigator:\n"
        "1. The officer taps their government RFID identity badge against the scanner.\n"
        "2. The officer places their thumb on the optical fingerprint sensor.\n"
        "3. The terminal instantly verifies both items against the secure database. If either the card or the fingerprint "
        "is unrecognized, access is denied and a security alarm is logged.\n"
        "4. (Testing / Simulation Mode): When physical hardware is not present, investigators can use the built-in "
        "Simulation Mode in the app header to simulate tapping Card '04A1B2C3' and Fingerprint 'ID 12' with one click."
    )
    pdf.draw_highlight_box("Step 1 Summary", [
        "Guarantees that only genuine, verified personnel can touch evidence.",
        "Eliminates stolen password attacks by requiring physical badge + biological fingerprint.",
        "Works smoothly in Simulation Mode for training, testing, and demonstrations."
    ], box_color="green")

    pdf.ln(3)
    pdf.draw_step_header("2", "Opening an Official Case File", "Setting up the investigation container")
    pdf.draw_text(
        "Before any evidence files are uploaded, an investigator creates a formal Case File. This acts as the legal folder "
        "for the entire investigation."
    )
    pdf.draw_text(
        "What the user enters:\n"
        "- Case Title (e.g., 'Operation Red Dawn - Corporate Breach')\n"
        "- Incident Description (What happened, when it occurred, where it took place)\n"
        "- Priority Level: LOW, MEDIUM, HIGH, or CRITICAL\n"
        "- Assigned Lead Investigator\n\n"
        "What the system does automatically:\n"
        "The system generates a permanent, tamper-proof Case ID in the official format: DF-2026-000001. "
        "This number will follow all exhibits and courtroom filings throughout the lifetime of the case."
    )
    pdf.draw_highlight_box("Step 2 Summary", [
        "Creates a central organized home for all exhibits, suspect files, and timelines.",
        "Prevents case number collisions with automated sequential numbering (DF-YYYY-XXXXXX).",
        "Records the exact creator and timestamp in the permanent audit trail."
    ], box_color="blue")

    # ============================================================
    # PAGE 3: STEPS 3 & 4 (EVIDENCE VAULT & METADATA)
    # ============================================================
    pdf.add_page()
    pdf.draw_step_header("3", "Depositing Evidence into the Digital Vault", "Safe storage and instant digital fingerprinting")
    pdf.draw_text(
        "When an officer seizes a phone photo, an email file, a server log, or a USB drive, they open the case's "
        "'Evidence Vault' tab and upload the file."
    )
    pdf.draw_text(
        "The Magic of Cryptographic Fingerprinting (SHA-256):\n"
        "The very instant the file uploads, the system calculates its SHA-256 digital fingerprint. Think of this as a unique "
        "64-character DNA code for the file. For example:\n"
        "  '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'\n\n"
        "If even one single pixel in a photograph or one single letter in a 1,000-page document is changed later, "
        "this DNA code completely changes. The system saves this original DNA code as the permanent baseline."
    )
    pdf.draw_highlight_box("Step 3 Summary", [
        "Files are immediately locked in a sandboxed, protected server vault.",
        "Calculates the digital fingerprint on the fly without bogging down computer memory.",
        "Guarantees that the evidence deposited today is identical to what is shown in court tomorrow."
    ], box_color="green")

    pdf.ln(3)
    pdf.draw_step_header("4", "Automatic Detective Work (Metadata Extraction)", "Uncovering hidden clues automatically")
    pdf.draw_text(
        "Digital files contain extensive hidden background information called 'metadata'. As soon as a file is deposited, "
        "the system's built-in forensic scanner dissects it in seconds:"
    )
    pdf.draw_text(
        "- Photographs (JPEG/PNG): Extracts the exact camera/phone model, shutter speed, exact date and time the photo was taken, "
        "and GPS coordinates (latitude, longitude, altitude) pin-pointing where the suspect was standing.\n"
        "- Spreadsheets & Databases (CSV/JSON): Reads column titles, row counts, and data patterns.\n"
        "- ZIP & Compressed Archives: Catalogs every file hidden inside without needing manual extraction.\n"
        "- Documents & Text Files: Counts lines, checks encoding, and indexes key keywords for immediate discovery."
    )
    pdf.draw_highlight_box("Step 4 Summary", [
        "Saves investigators hours of manual file inspection.",
        "Uncovers geographic locations (GPS) and exact camera models automatically.",
        "Indexes all discoveries into the case's intelligence database."
    ], box_color="amber")

    # ============================================================
    # PAGE 4: STEPS 5 & 6 (CHAIN OF CUSTODY & TIMELINE)
    # ============================================================
    pdf.add_page()
    pdf.draw_step_header("5", "Auditing the Chain of Custody & Tamper Checks", "Proving who touched the evidence and when")
    pdf.draw_text(
        "In a trial, defense attorneys often ask: 'How do we know someone didn't secretly edit this file?'\n"
        "This platform provides two ironclad answers:"
    )
    pdf.draw_text(
        "A. The Digital Chain-of-Custody Logbook:\n"
        "Every time an investigator views, analyzes, transfers, or checks out an evidence file, a new entry is permanently "
        "written into the ledger. It records: Exactly who did it, what time it happened, why they did it, and the file's current hash.\n\n"
        "B. One-Click 'Verify Integrity' Button:\n"
        "At any time, an investigator or auditor can click 'Verify Integrity'. The computer re-scans the file on disk and compares "
        "its current DNA code to its intake baseline. If they match, a green badge displays: [VERIFIED - 0 BIT DRIFT]. "
        "If someone tried to modify the file, it instantly turns red: [TAMPERED] and triggers a high-severity emergency alert."
    )
    pdf.draw_highlight_box("Step 5 Summary", [
        "Unbroken paper trail without messy physical sign-out sheets.",
        "Immediate detection if a file was corrupted, edited, or infected by malware.",
        "Full compliance with ISO/IEC 27037 international digital evidence standards."
    ], box_color="green")

    pdf.ln(3)
    pdf.draw_step_header("6", "The Master Forensic Timeline", "Reconstructing the crime step-by-step")
    pdf.draw_text(
        "A crime is rarely a single event; it is a chain of events over minutes, hours, or days. The platform's "
        "'Forensic Timeline' unifies disparate pieces of the puzzle into a single chronological interactive timeline:"
    )
    pdf.draw_text(
        "The system merges:\n"
        "1. Physical photo capture dates from suspect cameras\n"
        "2. File upload and modification times\n"
        "3. Investigator field notes and suspect interviews\n"
        "4. Ingestion terminal badge taps and lab access logs\n\n"
        "Investigators can filter by date range, search by keywords, or filter by severity (Critical, Warning, Info) "
        "to tell the complete story clearly to a jury."
    )
    pdf.draw_highlight_box("Step 6 Summary", [
        "Translates disconnected files into a clear, understandable timeline of events.",
        "Handles exact times, approximate estimates, and time-zone discrepancies cleanly.",
        "Allows fast filtering so examiners can find key moments in seconds."
    ], box_color="blue")

    # ============================================================
    # PAGE 5: STEPS 7 & 8 (AI GRAPH, RISK & COURT REPORT)
    # ============================================================
    pdf.add_page()
    pdf.draw_step_header("7", "Visualizing Connections & AI Risk Scoring", "Connecting the dots and finding hidden threats")
    pdf.draw_text(
        "Investigators often suffer from information overload. The system uses visual mapping and artificial intelligence "
        "to highlight the most critical risks:"
    )
    pdf.draw_text(
        "A. The Interactive Evidence Graph:\n"
        "On the 'Evidence Graph' tab, the screen draws an interactive web showing how suspects, evidence files, "
        "custodians, and timeline events connect to one another. Clicking any bubble reveals its relationships.\n\n"
        "B. The 0 to 100 Risk Score (Objective Math):\n"
        "The system calculates a clear risk gauge: Green (Low Risk, <35), Amber (Medium Risk, 35-69), or Red (High Risk, 70+). "
        "If an exhibit has been tampered with or critical security breaches were found, the score immediately jumps to Red.\n\n"
        "C. AI Threat Assistant (Google Gemini + Offline Rules):\n"
        "The built-in AI analyzes the entire case and produces two clear sections: (1) Certified Facts (undeniable data) "
        "and (2) Potential Interpretations (suspect intent and attack vectors), followed by immediate recommended next steps."
    )
    pdf.draw_highlight_box("Step 7 Summary", [
        "Visual graph simplifies complex multi-suspect corporate or cyber investigations.",
        "Mathematical risk score removes investigator guesswork and bias.",
        "Separates hard facts from AI opinions so testimony remains credible in court."
    ], box_color="amber")

    pdf.ln(3)
    pdf.draw_step_header("8", "One-Click Court-Admissible PDF Report", "Delivering certified proof to the courtroom")
    pdf.draw_text(
        "Once the investigation is complete, the investigator navigates to the 'Court Reports' tab and clicks 'Generate Report'. "
        "In under 3 seconds, the system compiles an official, multi-page legal document containing: Case overview, "
        "all exhibits with full SHA-256 fingerprints, integrity test results, timeline, and complete chain-of-custody logs."
    )
    pdf.draw_text(
        "The Cryptographic Digital Seal:\n"
        "When the PDF is created, the system locks it with a digital seal (a SHA-256 hash of the entire document). "
        "When a judge or opposing counsel downloads the file, the system checks the seal. If even a single word in the PDF "
        "was modified, the seal breaks, proving the document has been tampered with."
    )
    pdf.draw_highlight_box("Step 8 Summary", [
        "Generates publication-grade, court-admissible PDF reports in seconds.",
        "Every report is sealed cryptographically so it cannot be falsified.",
        "Includes examiner signature block and compliance citations for legal admissibility."
    ], box_color="green")

    # ============================================================
    # PAGE 6: QUICK REFERENCE CHEAT SHEET
    # ============================================================
    pdf.add_page()
    pdf.draw_step_header("9", "Quick Reference: 5-Minute End-User Cheat Sheet", "Step-by-step summary for daily operations")

    quick_steps = [
        ["1. Login", "Open app (http://localhost:5173). Sign in with email/password or use the Hardware Simulation card in the header."],
        ["2. Start Case", "Click 'Cases' -> '+ New Case'. Enter title, description, and priority level."],
        ["3. Upload Evidence", "In Case Detail, click 'Evidence Vault'. Drag and drop seized photos, documents, or logs."],
        ["4. Review Findings", "Click on any uploaded file to see extracted camera metadata, GPS locations, and SHA-256 hashes."],
        ["5. Verify Integrity", "Click 'Verify Integrity' on any exhibit. Look for the green [VERIFIED - 0 BIT DRIFT] badge."],
        ["6. Check Timeline", "Click 'Forensic Timeline' to view the chronological progression of events and filter by dates."],
        ["7. Explore Graph", "Click 'Evidence Graph' to see a visual map connecting suspects, files, and timeline nodes."],
        ["8. AI Analysis", "Click 'AI Risk & Recommendations' -> 'Run Analysis' to see risk score and prioritized action steps."],
        ["9. Export Report", "Click 'Court Reports' -> 'Compile New Report'. Download the sealed PDF for legal presentation."]
    ]

    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_font("helvetica", "B", 8.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(35, 6, "STAGE", border=1, align="C", fill=True)
    pdf.cell(155, 6, "WHAT YOU DO IN THE APP", border=1, align="L", fill=True)
    pdf.ln(6)

    for i, row in enumerate(quick_steps):
        if i % 2 == 0:
            pdf.set_fill_color(248, 250, 252)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(35, 6.5, _safe_text(row[0]), border=1, fill=True)
        pdf.set_font("helvetica", "", 8)
        pdf.cell(155, 6.5, _safe_text(row[1]), border=1, fill=True)
        pdf.ln(6.5)

    pdf.ln(5)
    pdf.draw_highlight_box("Default User Accounts (Ready for Immediate Login)", [
        "Chief Investigator (Admin): admin@forensics.gov | password123 (Full control)",
        "Forensic Analyst (Investigator): investigator@forensics.gov | password123 (Case & evidence handling)",
        "Court Auditor (Viewer): viewer@forensics.gov | password123 (Read-only legal review)"
    ], box_color="blue")

    pdf.output(output_path)
    print(f"[+] Successfully generated End-User Guide PDF at: {output_path}")

if __name__ == "__main__":
    out_file = os.path.abspath(r"d:\Macro\End_User_Workflow_Guide.pdf")
    generate_end_user_pdf(out_file)
    hasher = hashlib.sha256()
    with open(out_file, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    print(f"[+] SHA-256 Seal: {hasher.hexdigest()}")
    print(f"[+] File Size: {os.path.getsize(out_file)} bytes")
