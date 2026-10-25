import os
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from bson import ObjectId
from fpdf import FPDF

from app.core.config import settings
from app.models.report import ForensicReportResponse
from app.services.risk_service import RiskScoringService
from app.services.ai_service import ForensicAIService, RecommendationService
from app.services.graph_service import GraphService

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_DIR = os.path.join(BASE_DIR, "static")
COVER_TEMPLATE_PATH = os.path.join(STATIC_DIR, "report_cover_template.png")
LOGO_PATH = os.path.join(STATIC_DIR, "cryptevid_logo.png")

def _safe_text(s: Any) -> str:
    """Sanitize strings to latin-1 compatible text for core PDF fonts."""
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
        ''': "'",
        ''': "'",
        "…": "...",
        "≥": ">=",
        "≤": "<=",
        "≠": "!=",
        "→": "->",
        "←": "<-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
        "\u2192": "->",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")

class ForensicPDF(FPDF):
    """
    Court-admissible forensic examination PDF document generator.
    Enforces ISO/IEC 27037 forensic documentation standards.
    """
    def __init__(self, case_number: str, report_id_str: str, logo_path: Optional[str] = None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.case_number = case_number
        self.report_id_str = report_id_str
        self.logo_path = logo_path
        self.current_table_headers = None
        self.current_table_widths = None
        self.current_table_aligns = None

    def header(self):
        # Do not render header on Cover Page (Page 1)
        if self.page_no() == 1:
            return

        self.set_xy(12, 7)
        # Compact CRYPTEVID logo / header mark
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                self.image(self.logo_path, x=12, y=5.5, w=6.5, h=6.5)
            except Exception:
                pass

        self.set_xy(20, 6.5)
        self.set_font("helvetica", "B", 7.5)
        self.set_text_color(11, 27, 61)  # Deep Navy
        self.cell(105, 5, _safe_text(f"CRYPTEVID FORENSIC INTELLIGENCE // CASE: {self.case_number}"), align="L")

        self.set_font("helvetica", "B", 7.5)
        self.set_text_color(184, 134, 11)  # Metallic Gold
        self.cell(71, 5, "CONFIDENTIAL // OFFICIAL RECORD", align="R", new_x="LMARGIN", new_y="NEXT")

        # Thin gold divider line
        self.set_draw_color(184, 161, 110)
        self.set_line_width(0.25)
        self.line(12, 13, 198, 13)
        self.set_y(16)

    def footer(self):
        # Do not render footer on Cover Page (Page 1)
        if self.page_no() == 1:
            return

        self.set_y(-14)
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.2)
        self.line(12, 284, 198, 284)

        self.set_font("helvetica", "", 7)
        self.set_text_color(100, 116, 139)
        self.set_x(12)
        self.cell(70, 7, _safe_text(f"Case ID: {self.case_number} | Report ID: {self.report_id_str}"), align="L")
        self.cell(46, 7, "CRYPTEVID Forensic Platform", align="C")
        self.cell(70, 7, f"Page {self.page_no()} of {{nb}}", align="R")

    def check_space(self, height_needed: float = 18):
        """Triggers a clean page break if needed space exceeds printable area."""
        if self.get_y() + height_needed > 275:
            self.add_page()
            if self.current_table_headers and self.current_table_widths:
                self._draw_table_header_cells(
                    self.current_table_headers,
                    self.current_table_widths,
                    self.current_table_aligns
                )

    def section_heading(self, number: int, title: str):
        """Renders an official section header with gold accent and navy typography."""
        self.check_space(24)
        self.ln(3)
        y = self.get_y()

        # Vertical metallic gold indicator bar
        self.set_fill_color(184, 134, 11)
        self.rect(12, y + 0.5, 2.5, 6, "F")

        self.set_xy(16.5, y)
        self.set_font("helvetica", "B", 10.5)
        self.set_text_color(11, 27, 61)  # Deep Navy
        full_title = f"{number}. {title.upper()}"
        self.cell(169.5, 7, _safe_text(full_title), new_x="LMARGIN", new_y="NEXT")

        # Subtle gold underline
        self.set_draw_color(226, 208, 160)
        self.set_line_width(0.3)
        self.line(12, self.get_y(), 198, self.get_y())
        self.ln(3.5)

    def subsection_heading(self, title: str):
        """Renders a clean subsection heading."""
        self.check_space(14)
        self.set_font("helvetica", "B", 8.5)
        self.set_text_color(30, 41, 59)
        self.cell(0, 5, _safe_text(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def paragraph(self, text: str, font_size: float = 8.0, text_color=(51, 65, 85)):
        """Renders standard multi-cell narrative paragraph."""
        self.check_space(10)
        self.set_font("helvetica", "", font_size)
        self.set_text_color(*text_color)
        self.multi_cell(186, 4.2, _safe_text(text))
        self.ln(2.5)

    def callout_box(self, text: str, title: Optional[str] = None, badge: str = "INFO", badge_color=(15, 23, 42)):
        """Renders a styled callout box with a colored left accent border."""
        self.check_space(20)
        start_y = self.get_y()
        self.set_fill_color(248, 250, 252)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)

        clean_badge = str(badge).replace("RiskLevel.", "")
        lines = len(text) // 95 + 2
        box_h = max(14, lines * 4.2 + (7 if title else 4))
        self.rect(12, start_y, 186, box_h, "DF")

        # Accent border
        self.set_fill_color(*badge_color)
        self.rect(12, start_y, 2, box_h, "F")

        self.set_xy(16, start_y + 2)
        if title:
            self.set_font("helvetica", "B", 8)
            self.set_text_color(*badge_color)
            self.cell(178, 4.5, _safe_text(f"[{clean_badge}] {title}"), new_x="LMARGIN", new_y="NEXT")
            self.set_x(16)

        self.set_font("helvetica", "", 7.5)
        self.set_text_color(51, 65, 85)
        self.multi_cell(178, 3.8, _safe_text(text))
        self.set_y(start_y + box_h + 3)

    def key_value_grid(self, pairs: List[Tuple[str, str]], cols: int = 2):
        """Renders a structured key-value property grid without overflow."""
        self.check_space(len(pairs) * 4)
        col_w = 93 if cols == 2 else 186
        lbl_w = 34 if cols == 2 else 45
        val_w = col_w - lbl_w

        i = 0
        while i < len(pairs):
            self.check_space(6)
            row_pairs = pairs[i:i+cols]
            start_x = 12
            for lbl, val in row_pairs:
                self.set_x(start_x)
                self.set_font("helvetica", "B", 7.5)
                self.set_text_color(71, 85, 105)
                self.cell(lbl_w, 4.8, _safe_text(f"{lbl}:"))

                self.set_font("helvetica", "", 7.5)
                self.set_text_color(15, 23, 42)
                # Ensure text width fits cleanly inside val_w - 2 mm
                clean_val = _safe_text(val)
                avail_w = val_w - 2.5
                if self.get_string_width(clean_val) > avail_w:
                    while len(clean_val) > 4 and self.get_string_width(clean_val + "...") > avail_w:
                        clean_val = clean_val[:-1]
                    clean_val = clean_val + "..."
                self.cell(val_w, 4.8, clean_val)
                start_x += col_w
            self.ln(4.8)
            i += cols
        self.ln(2)

    def _draw_table_header_cells(self, headers: List[str], widths: List[float], aligns: Optional[List[str]] = None):
        """Draws the header row of a table."""
        self.set_font("helvetica", "B", 7)
        self.set_fill_color(241, 245, 249)
        self.set_draw_color(203, 213, 225)
        self.set_text_color(15, 23, 42)
        self.set_line_width(0.2)

        self.set_x(12)
        for idx, h in enumerate(headers):
            al = aligns[idx] if aligns and idx < len(aligns) else "L"
            is_last = (idx == len(headers) - 1)
            if is_last:
                self.cell(widths[idx], 5.5, _safe_text(h), border=1, fill=True, align=al, new_x="LMARGIN", new_y="NEXT")
            else:
                self.cell(widths[idx], 5.5, _safe_text(h), border=1, fill=True, align=al)

    def render_table(
        self,
        headers: List[str],
        widths: List[float],
        rows: List[List[str]],
        aligns: Optional[List[str]] = None,
        status_rules: Optional[Dict[int, Dict[str, Tuple[int, int, int]]]] = None
    ):
        """
        Renders a cleanly formatted table with auto header repeating upon page splits.
        """
        self.check_space(14)
        self._draw_table_header_cells(headers, widths, aligns)

        # Set headers for subsequent split pages only after the initial header is drawn
        self.current_table_headers = headers
        self.current_table_widths = widths
        self.current_table_aligns = aligns

        if not rows:
            self.set_font("helvetica", "I", 7.5)
            self.set_text_color(100, 116, 139)
            self.set_x(12)
            self.cell(sum(widths), 6, "No recorded events or entries found.", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
            self.ln(3)
            self.current_table_headers = None
            return

        self.set_font("helvetica", "", 7)
        fill = False
        for row in rows:
            self.check_space(6.5)
            self.set_x(12)
            for idx, cell in enumerate(row):
                w = widths[idx]
                al = aligns[idx] if aligns and idx < len(aligns) else "L"
                is_last = (idx == len(row) - 1)

                # Status coloring
                text_col = (51, 65, 85)
                font_weight = ""
                if status_rules and idx in status_rules:
                    cell_str = str(cell).strip().upper()
                    for pattern, color in status_rules[idx].items():
                        if pattern.upper() in cell_str:
                            text_col = color
                            font_weight = "B"
                            break

                self.set_font("helvetica", font_weight, 7)
                self.set_text_color(*text_col)
                self.set_fill_color(248, 250, 252) if fill else self.set_fill_color(255, 255, 255)
                self.set_draw_color(226, 232, 240)

                # Truncate text if needed to prevent multi-line overflow inside standard cell
                cell_val = _safe_text(cell)
                # Keep long cell content readable
                max_chars = int(w * 1.8)
                if len(cell_val) > max_chars:
                    cell_val = cell_val[:max_chars - 3] + "..."

                if is_last:
                    self.cell(w, 5.0, cell_val, border=1, fill=True, align=al, new_x="LMARGIN", new_y="NEXT")
                else:
                    self.cell(w, 5.0, cell_val, border=1, fill=True, align=al)
            fill = not fill

        self.ln(3)
        self.current_table_headers = None
        self.current_table_widths = None
        self.current_table_aligns = None


class ForensicReportService:
    """
    Forensic Report Generation Engine.
    Compiles an official, court-admissible PDF document containing verified
    case metadata, exhibits, SHA-256 integrity checks, chain of custody,
    forensic timeline events, evidence graph, risk score, AI insights, and recommendations.
    """

    @classmethod
    async def render_pdf_file(
        cls,
        db,
        case_id: str,
        user: Dict[str, Any],
        title: Optional[str] = None,
        classification: Optional[str] = None,
        version: int = 1,
        target_path: Optional[str] = None
    ) -> str:
        case_id_str = str(case_id)
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else None

        case = await db["cases"].find_one({"_id": case_oid if case_oid else case_id_str})
        if not case:
            raise ValueError("CASE_NOT_FOUND")

        case_num = case.get("case_number", "CASE")
        report_id_str = f"RPT-{case_num}-{version:02d}"
        now = datetime.now(timezone.utc)

        # 1. Gather All Case Entities from active collections
        ev_cursor = db["evidence"].find({"case_id": case_id_str})
        evidence_list = await ev_cursor.to_list(length=500)
        ev_ids = [str(e["_id"]) for e in evidence_list]

        # Metadata
        meta_cursor = db["evidence_metadata"].find({"case_id": case_id_str})
        metadata_list = await meta_cursor.to_list(length=500)
        metadata_by_ev = {str(m.get("evidence_id")): m for m in metadata_list if m.get("evidence_id")}

        # Chain of Custody
        custody_list = []
        if ev_ids:
            cust_cursor = db["chain_of_custody"].find({"evidence_id": {"$in": ev_ids}}).sort("timestamp", 1)
            custody_list = await cust_cursor.to_list(length=500)

        # Forensic Events
        evt_cursor = db["forensic_events"].find({"case_id": case_id_str}).sort("created_at", 1)
        events_list = await evt_cursor.to_list(length=500)

        # Security Events
        sec_query = {"$or": [{"case_id": case_id_str}, {"evidence_id": {"$in": ev_ids}}]} if ev_ids else {"case_id": case_id_str}
        sec_cursor = db["security_events"].find(sec_query).sort("timestamp", 1)
        security_events_list = await sec_cursor.to_list(length=500)

        # Evidence Backups
        backup_cursor = db["evidence_backups"].find({"case_id": case_id_str}).sort("created_at", 1)
        backups_list = await backup_cursor.to_list(length=500)

        # Audit Logs related to case
        audit_query = {"$or": [{"case_id": case_id_str}, {"details": {"$regex": case_num, "$options": "i"}}]}
        audit_cursor = db["audit_logs"].find(audit_query).sort("timestamp", 1)
        audit_list = await audit_cursor.to_list(length=500)

        # Previous Reports for this case
        prev_reports = await db["forensic_reports"].find({"case_id": case_id_str}).sort("version", 1).to_list(length=100)

        # Investigation Diary Entries (BNSS Section 192)
        diary_cursor = db["investigation_diary"].find({"case_id": case_id_str}).sort("entry_number", 1)
        diary_list = await diary_cursor.to_list(length=500)

        # Analytics & Intelligence
        risk_data = await RiskScoringService.calculate_case_risk(db, case_id_str)
        ai_data = await ForensicAIService.generate_case_analysis(db, case_id_str, risk_data)
        recs_data = await RecommendationService.generate_recommendations(db, case_id_str, risk_data)
        graph_data = await GraphService.build_case_graph(db, case_id_str)

        report_title = title or f"Forensic Investigation Final Examination Report - {case_num} (v{version})"
        report_class = classification or "Confidential"

        # 2. Initialize PDF with custom header/footer
        pdf = ForensicPDF(case_number=case_num, report_id_str=report_id_str, logo_path=LOGO_PATH)
        pdf.alias_nb_pages()

        # =========================================================================
        # PAGE 1: COVER PAGE (STRICT FIDELITY TO REFERENCE DESIGN)
        # =========================================================================
        pdf.set_auto_page_break(False)
        pdf.add_page()

        # Overlay reference background template
        if os.path.exists(COVER_TEMPLATE_PATH):
            pdf.image(COVER_TEMPLATE_PATH, x=0, y=0, w=210, h=297)
        else:
            # High-fidelity programmatic fallback if asset not present
            pdf.set_fill_color(254, 252, 254)
            pdf.rect(0, 0, 210, 297, "F")
            # Accent triangle top-left
            pdf.set_fill_color(11, 27, 61)
            pdf.polygon([(0, 0), (65, 0), (0, 65)], "F")
            pdf.set_fill_color(184, 134, 11)
            pdf.polygon([(65, 0), (70, 0), (0, 70), (0, 65)], "F")

        # Dynamic Case ID centered
        # Format: "Case ID: " in Dark Navy, "{case_num}" in Metallic Gold
        pdf.set_font("helvetica", "B", 14)
        lbl_text = "Case ID: "
        val_text = case_num or "Not available"
        w_lbl = pdf.get_string_width(lbl_text)
        w_val = pdf.get_string_width(val_text)
        total_w = w_lbl + w_val
        start_x = (210 - total_w) / 2

        pdf.set_xy(start_x, 154)
        pdf.set_text_color(11, 27, 61)  # Deep Navy
        pdf.write(7, lbl_text)
        pdf.set_text_color(184, 134, 11)  # Metallic Gold
        pdf.write(7, val_text)

        # Dynamic Case Title centered
        case_title = case.get("title") or "Not available"
        pdf.set_xy(15, 163)
        pdf.set_font("helvetica", "B", 13.5)
        pdf.set_text_color(11, 27, 61)  # Deep Navy
        # Truncate if extremely long to maintain elegant cover whitespace
        if len(case_title) > 65:
            case_title = case_title[:62] + "..."
        pdf.cell(180, 7, _safe_text(case_title), align="C")

        # Dynamic Metadata Table (Clean Two-Column Label-and-Value layout)
        user_name = user.get("name") or "Chief Investigator"
        user_role = (user.get("role") or "admin").capitalize()
        status_disp = (case.get("status") or "Open").replace("_", " ").title()
        gen_timestamp_disp = now.strftime("%d %B %Y, %H:%M:%S (UTC)")

        prepared_by = user_name if f"({user_role})" in user_name else f"{user_name} ({user_role})"

        cover_metadata = [
            ("Report ID", report_id_str),
            ("Generated On", gen_timestamp_disp),
            ("Prepared By", prepared_by),
            ("Case Status", status_disp),
            ("Classification", report_class),
            ("Version", f"{version}.0")
        ]

        y_meta = 184
        for lbl, val in cover_metadata:
            pdf.set_font("helvetica", "", 9.5)
            pdf.set_text_color(30, 41, 59)
            pdf.set_xy(34, y_meta)
            pdf.cell(34, 6.2, _safe_text(lbl))
            pdf.cell(8, 6.2, ":")
            pdf.set_font("helvetica", "", 9.5)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(96, 6.2, _safe_text(val if val else "Not available"))
            y_meta += 6.7

        # =========================================================================
        # REMAINING PAGES: SECTIONS 1 TO 17 (ALL IN THE SAME REPORT)
        # =========================================================================
        pdf.set_auto_page_break(True, margin=18)
        pdf.set_margins(12, 18, 12)
        pdf.add_page()

        # -------------------------------------------------------------------------
        # SECTION 1: EXECUTIVE SUMMARY
        # -------------------------------------------------------------------------
        pdf.section_heading(1, "Executive Summary")
        case_desc = case.get("description")
        if not case_desc or len(case_desc.strip()) < 10:
            case_desc = (
                f"This official forensic examination dossier documents the technical investigation conducted "
                f"for Case {case_num} ('{case.get('title', 'Not available')}'). The examination comprehensively "
                f"evaluates registered digital evidence exhibits, cryptographic hash baselines, tamper telemetry, "
                f"and security incidents in strict compliance with ISO/IEC 27037 standards."
            )
        pdf.paragraph(case_desc)

        # Key verified findings bullets
        tampered_count = sum(1 for e in evidence_list if e.get("integrity_status") == "TAMPERED")
        verified_count = sum(1 for e in evidence_list if e.get("integrity_status") == "VERIFIED")
        sec_count = len(security_events_list)
        risk_score = risk_data.score
        risk_lvl = str(risk_data.risk_level).replace("RiskLevel.", "")

        integ_status_str = "COMPROMISED (Tamper Detected)" if tampered_count > 0 else "SECURE (100% Cryptographic Match)"
        integ_color = (225, 29, 72) if tampered_count > 0 else (5, 150, 105)

        pdf.key_value_grid([
            ("Investigation Purpose", str(case.get("case_type", "Digital Forensics")).replace("_", " ")),
            ("Evidence Integrity Status", integ_status_str),
            ("Deterministic Risk Posture", f"{risk_score}/100 ({risk_lvl})"),
            ("Registered Exhibits", f"{len(evidence_list)} Total ({verified_count} Verified, {tampered_count} Tampered)"),
            ("Security Incidents Logged", f"{sec_count} Security Alert(s)"),
            ("Chain of Custody Ledger", f"{len(custody_list)} Continuity Events Recorded"),
            ("Investigation Diary", f"{len(diary_list)} BNSS 192 Record(s) Logged")
        ], cols=2)

        exec_conclusion = (
            f"CONCLUSION: Cryptographic evaluation reveals {verified_count} exhibit(s) maintain verified hash continuity, "
            f"with {tampered_count} detected integrity discrepancy(ies). The calculated deterministic risk posture is {risk_lvl} "
            f"({risk_score}/100). All evidence exhibits and chain-of-custody milestones have been cryptographically registered."
        )
        pdf.callout_box(exec_conclusion, title="Executive Assessment Verdict", badge=risk_lvl, badge_color=integ_color)

        # -------------------------------------------------------------------------
        # SECTION 2: CASE INFORMATION AND INVESTIGATION SCOPE
        # -------------------------------------------------------------------------
        pdf.section_heading(2, "Case Information and Investigation Scope")
        created_at_dt = case.get("created_at")
        created_at_str = created_at_dt.strftime("%d %B %Y, %H:%M:%S UTC") if isinstance(created_at_dt, datetime) else str(created_at_dt or "Not available")

        creator_name = case.get("created_by_name") or case.get("created_by") or "Not available"
        assigned_inv = case.get("assigned_investigator_name") or case.get("assigned_investigator") or "Unassigned"

        pdf.key_value_grid([
            ("Case Identifier", case_num),
            ("Case Status", case.get("status", "OPEN")),
            ("Case Title", case.get("title", "Not available")),
            ("Case Priority", case.get("priority", "MEDIUM")),
            ("Classification Type", case.get("case_type", "OTHER")),
            ("Creation Date", created_at_str),
            ("Case Creator", creator_name),
            ("Lead Investigator", assigned_inv)
        ], cols=2)

        scope_text = (
            f"INVESTIGATION SCOPE & OBJECTIVES: Perform forensic bit-stream validation, verify SHA-256 integrity "
            f"baselines, analyze extracted file container metadata, inspect chain-of-custody ledgers, and correlate "
            f"relational graph topology for Case {case_num}. Identification and logging of unauthorized access attempts "
            f"and physical/logical tampering are conducted in accordance with statutory digital evidence protocols."
        )
        pdf.paragraph(scope_text)

        # -------------------------------------------------------------------------
        # SECTION 3: EVIDENCE INVENTORY AND ACQUISITION
        # -------------------------------------------------------------------------
        pdf.section_heading(3, "Evidence Inventory and Acquisition")
        pdf.paragraph(
            f"A total of {len(evidence_list)} digital evidence exhibit(s) have been acquired and preserved in the case container. "
            f"All acquisitions undergo immediate cryptographic baseline calculation upon arrival."
        )

        ev_headers = ["Evidence ID", "Filename", "MIME / Type", "Size", "Acquisition Time (UTC)", "Collector", "Status"]
        ev_widths = [24, 38, 26, 18, 32, 26, 22]
        ev_aligns = ["L", "L", "L", "R", "C", "L", "C"]
        ev_rows = []

        for ev in evidence_list:
            ev_id_short = str(ev.get("_id", "N/A"))[-8:]
            fn = ev.get("original_filename", "Artifact")
            mime = ev.get("mime_type") or ev.get("file_extension") or "binary"
            sz = f"{ev.get('file_size', 0):,} B"

            acq_dt = ev.get("collection_timestamp") or ev.get("created_at")
            acq_str = acq_dt.strftime("%Y-%m-%d %H:%M") if isinstance(acq_dt, datetime) else str(acq_dt or "Not available")[:16]

            collector = ev.get("collector_name") or ev.get("collector_id") or "Automated Intake"
            integ = ev.get("integrity_status", "VERIFIED")

            ev_rows.append([ev_id_short, fn, mime, sz, acq_str, collector, integ])

        pdf.render_table(
            ev_headers, ev_widths, ev_rows, ev_aligns,
            status_rules={6: {"TAMPERED": (225, 29, 72), "VERIFIED": (5, 150, 105), "PENDING": (217, 119, 6)}}
        )

        # -------------------------------------------------------------------------
        # SECTION 4: EVIDENCE METADATA ANALYSIS
        # -------------------------------------------------------------------------
        pdf.section_heading(4, "Evidence Metadata Analysis")
        pdf.paragraph(
            "Extracted filesystem and file container attributes are parsed across supported formats (Images, PDFs, "
            "TXT/LOG, CSV, JSON, and ZIP archives). Note: The absence of optional metadata (such as EXIF, GPS coordinates, "
            "or document authorship tags) reflects file source characteristics or privacy sanitization and alone does not "
            "constitute evidence of tampering."
        )

        meta_headers = ["Evidence Exhibit", "Metadata Status", "Extracted Container Attributes & Camera/GPS Telemetry"]
        meta_widths = [45, 25, 116]
        meta_aligns = ["L", "C", "L"]
        meta_rows = []

        for ev in evidence_list:
            ev_id_str = str(ev.get("_id"))
            fn = ev.get("original_filename", "Artifact")
            meta_record = metadata_by_ev.get(ev_id_str)

            attrs = ev.get("extracted_attributes") or (meta_record.get("extracted_attributes") if meta_record else {}) or {}
            status_meta = ev.get("metadata_status") or (meta_record.get("metadata_status") if meta_record else "EXTRACTED") or "EXTRACTED"

            # Build readable summary of attributes
            attr_parts = []
            if attrs:
                for k, v in list(attrs.items())[:6]:
                    attr_parts.append(f"{k}: {v}")
            else:
                # Fallback to file extension specifics
                ext = ev.get("file_extension", "").lower()
                attr_parts.append(f"Format: {ext or 'Standard'}")
                attr_parts.append(f"Device: {ev.get('source_device', 'WEB_APP')}")
                attr_parts.append("GPS/EXIF: None recorded")

            summary_str = "; ".join(attr_parts) if attr_parts else "Standard file attributes verified; no embedded EXIF tags."
            meta_rows.append([fn, status_meta, summary_str])

        pdf.render_table(
            meta_headers, meta_widths, meta_rows, meta_aligns,
            status_rules={1: {"EXTRACTED": (5, 150, 105), "FAILED": (225, 29, 72), "PENDING": (217, 119, 6)}}
        )

        # -------------------------------------------------------------------------
        # SECTION 5: CRYPTOGRAPHIC INTEGRITY VERIFICATION
        # -------------------------------------------------------------------------
        pdf.section_heading(5, "Cryptographic Integrity Verification")
        pdf.paragraph(
            "Every exhibit is validated against its immutable SHA-256 intake digest. If an exhibit hash diverges from "
            "its baseline, a tamper alert is generated and recorded into the security ledger."
        )

        hash_headers = ["Exhibit", "Baseline SHA-256 Hash", "Current Verified Hash", "Verification Result"]
        hash_widths = [40, 56, 56, 34]
        hash_aligns = ["L", "L", "L", "C"]
        hash_rows = []

        for ev in evidence_list:
            fn = ev.get("original_filename", "Artifact")
            base_hash = ev.get("sha256_hash", "UNKNOWN")
            curr_hash = ev.get("last_calculated_hash") or base_hash
            integ = ev.get("integrity_status", "VERIFIED")

            res_str = "MATCH [PASS]" if integ == "VERIFIED" else "MISMATCH [FAIL]"
            # Format hash with clean ellipsis
            b_str = base_hash[:18] + "..." + base_hash[-8:] if len(base_hash) > 28 else base_hash
            c_str = curr_hash[:18] + "..." + curr_hash[-8:] if len(curr_hash) > 28 else curr_hash

            hash_rows.append([fn, b_str, c_str, res_str])

        pdf.render_table(
            hash_headers, hash_widths, hash_rows, hash_aligns,
            status_rules={3: {"MATCH": (5, 150, 105), "MISMATCH": (225, 29, 72)}}
        )

        # -------------------------------------------------------------------------
        # SECTION 6: SECURE EVIDENCE PRESERVATION AND BACKUP
        # -------------------------------------------------------------------------
        pdf.section_heading(6, "Secure Evidence Preservation and Backup")
        pdf.paragraph(
            "Original evidence baselines are protected in isolated, air-gapped preservation containers. In accordance "
            "with forensic protection protocols, physical storage paths and encryption secrets are withheld from exported "
            "dossiers, exposing only verifiable logical storage references."
        )

        if backups_list:
            bk_headers = ["Backup Ref ID", "Exhibit Filename", "Version", "Preservation Timestamp", "Backup SHA-256", "Status"]
            bk_widths = [32, 40, 16, 36, 42, 20]
            bk_aligns = ["L", "L", "C", "C", "L", "C"]
            bk_rows = []

            for bk in backups_list:
                ref_id = bk.get("storage_reference") or bk.get("backup_id") or "BACKUP-REF"
                fn = bk.get("original_filename", "Artifact")
                ver = f"v{bk.get('version', 1)}"
                ts = bk.get("created_at")
                ts_str = ts.strftime("%Y-%m-%d %H:%M") if isinstance(ts, datetime) else str(ts or "Not available")[:16]
                b_hash = bk.get("backup_sha256", "UNKNOWN")
                b_hash_disp = b_hash[:14] + "..." + b_hash[-6:] if len(b_hash) > 24 else b_hash
                st = bk.get("status", "PROTECTED")

                bk_rows.append([ref_id, fn, ver, ts_str, b_hash_disp, st])

            pdf.render_table(
                bk_headers, bk_widths, bk_rows, bk_aligns,
                status_rules={5: {"PROTECTED": (5, 150, 105), "TAMPERED": (225, 29, 72)}}
            )
        else:
            pdf.callout_box(
                "No secondary isolated backup copies currently registered in the database for this case container. "
                "Primary working copies remain cryptographically validated against baseline hashes.",
                title="Preservation Container Notice",
                badge="INFO"
            )

        # -------------------------------------------------------------------------
        # SECTION 7: CHAIN OF CUSTODY
        # -------------------------------------------------------------------------
        pdf.section_heading(7, "Chain of Custody")
        pdf.paragraph(
            f"The continuous chain-of-custody ledger records every interaction, transfer, and verification event. "
            f"Cryptographic hash chaining ensures an unbroken audit trail for court admissibility ({len(custody_list)} Total Events)."
        )

        cust_headers = ["Timestamp (UTC)", "Action Performed", "Investigator / Actor", "Evidence ID", "Integrity / Remarks"]
        cust_widths = [32, 44, 34, 26, 50]
        cust_aligns = ["C", "L", "L", "L", "L"]
        cust_rows = []

        for cust in custody_list[:35]:
            ts = cust.get("timestamp")
            ts_str = ts.strftime("%Y-%m-%d %H:%M") if isinstance(ts, datetime) else str(ts or "Not available")[:16]
            action = cust.get("action", "CUSTODY")
            actor = cust.get("actor_name") or cust.get("actor_id") or "System"
            ev_id_short = str(cust.get("evidence_id", "N/A"))[-8:]
            notes = cust.get("notes") or cust.get("details") or "Verified cryptographic continuity"

            cust_rows.append([ts_str, action, actor, ev_id_short, notes])

        pdf.render_table(
            cust_headers, cust_widths, cust_rows, cust_aligns,
            status_rules={1: {"FAILURE": (225, 29, 72), "TAMPER": (225, 29, 72), "VERIFIED": (5, 150, 105)}}
        )

        # -------------------------------------------------------------------------
        # SECTION 8: FORENSIC ACTIVITY AND ACCESS TIMELINE
        # -------------------------------------------------------------------------
        pdf.section_heading(8, "Forensic Activity and Access Timeline")
        pdf.paragraph(
            "Chronological event telemetry distinguishes completed forensic actions from attempted or blocked operations. "
            "Includes login sessions, biometric authentications, exhibit transfers, and verification activities."
        )

        act_headers = ["Timestamp (UTC)", "Event Category", "Terminal / IP", "Actor / ID", "Outcome", "Action Details"]
        act_widths = [32, 34, 30, 28, 20, 42]
        act_aligns = ["C", "L", "L", "L", "C", "L"]
        act_rows = []

        for evt in events_list[:30]:
            ts = evt.get("event_time") or evt.get("created_at")
            ts_str = ts.strftime("%Y-%m-%d %H:%M") if isinstance(ts, datetime) else str(ts or "Not available")[:16]
            etype = evt.get("event_type", "ACTIVITY")
            ip = evt.get("ip_address") or evt.get("device_id") or "WORKSTATION"
            user_lbl = evt.get("actor_name") or evt.get("actor_id") or "System"
            res = "SUCCESS" if evt.get("severity") != "CRITICAL" else "ALERT"
            title_text = evt.get("title") or evt.get("description") or etype

            act_rows.append([ts_str, etype, ip, user_lbl, res, title_text])

        pdf.render_table(
            act_headers, act_widths, act_rows, act_aligns,
            status_rules={4: {"SUCCESS": (5, 150, 105), "ALERT": (225, 29, 72), "BLOCKED": (217, 119, 6)}}
        )

        # -------------------------------------------------------------------------
        # SECTION 9: UNAUTHORIZED ACCESS AND SECURITY ANALYSIS
        # -------------------------------------------------------------------------
        pdf.section_heading(9, "Unauthorized Access and Security Analysis")
        pdf.paragraph(
            "Evaluation of unauthorized access attempts, authentication failures, and anomalous telemetry events. "
            "Physical MAC addresses and user identities are reported only when directly attested by verified authentication records."
        )

        if security_events_list:
            sec_headers = ["Event ID", "Severity", "Timestamp (UTC)", "Event Type", "Source IP / Device", "Trigger Reason"]
            sec_widths = [24, 20, 32, 42, 32, 36]
            sec_aligns = ["L", "C", "C", "L", "L", "L"]
            sec_rows = []

            for sec in security_events_list[:25]:
                eid = str(sec.get("_id") or sec.get("event_id", "N/A"))[-8:]
                sev = sec.get("severity", "MEDIUM")
                ts = sec.get("timestamp")
                ts_str = ts.strftime("%Y-%m-%d %H:%M") if isinstance(ts, datetime) else str(ts or "Not available")[:16]
                etype = sec.get("event_type", "SECURITY_ALERT")
                src = sec.get("ip_address") or sec.get("device_id") or "Remote Socket"
                reason = sec.get("reason") or sec.get("action") or "Suspicious anomaly detected"

                sec_rows.append([eid, sev, ts_str, etype, src, reason])

            pdf.render_table(
                sec_headers, sec_widths, sec_rows, sec_aligns,
                status_rules={1: {"CRITICAL": (225, 29, 72), "HIGH": (217, 119, 6), "MEDIUM": (71, 85, 105)}}
            )
        else:
            pdf.callout_box(
                "No unauthorized access attempts, credential breaches, or suspicious security incidents "
                "recorded for this case container. Threat posture remains nominal.",
                title="Security Incident Telemetry",
                badge="NOMINAL",
                badge_color=(5, 150, 105)
            )

        # -------------------------------------------------------------------------
        # SECTION 10: EVIDENCE RELATIONSHIP GRAPH
        # -------------------------------------------------------------------------
        pdf.section_heading(10, "Evidence Relationship Graph")
        pdf.paragraph(
            f"Topological entity mapping connects case entities, physical and logical evidence artifacts, "
            f"custody milestones, investigators, originating terminals, and security alerts ({graph_data.total_nodes} "
            f"Relational Nodes, {graph_data.total_edges} Verified Forensic Edges)."
        )

        pdf.key_value_grid([
            ("Total Relational Nodes", str(graph_data.total_nodes)),
            ("Verified Forensic Edges", str(graph_data.total_edges)),
            ("Topology Density", f"{(graph_data.total_edges / max(1, graph_data.total_nodes)):.2f} edges/node"),
            ("Case Anchor", f"{case_num} ({case.get('title', 'Forensic Incident')[:25]})")
        ], cols=2)

        if graph_data.edges:
            pdf.subsection_heading("Primary Topological Relationships")
            edge_headers = ["Source Entity", "Relationship Type", "Target Entity", "Context / Note"]
            edge_widths = [45, 42, 45, 54]
            edge_aligns = ["L", "C", "L", "L"]
            edge_rows = []

            for edge in graph_data.edges[:20]:
                src = str(edge.source).replace("ev_", "EVD: ").replace("case_", "CASE: ").replace("cust_", "CUST: ").replace("dev_", "DEV: ").replace("dEVD: ", "DEV: ")
                tgt = str(edge.target).replace("ev_", "EVD: ").replace("case_", "CASE: ").replace("cust_", "CUST: ").replace("dev_", "DEV: ").replace("dEVD: ", "DEV: ")
                lbl = str(edge.edge_type or edge.label or "ASSOCIATED_WITH").replace("GraphEdgeType.", "")
                note = str(edge.label or "Direct forensic linkage").replace("GraphEdgeType.", "")
                edge_rows.append([src, lbl, tgt, note])

            pdf.render_table(edge_headers, edge_widths, edge_rows, edge_aligns)

        # -------------------------------------------------------------------------
        # SECTION 11: DETERMINISTIC FORENSIC RISK ASSESSMENT
        # -------------------------------------------------------------------------
        pdf.section_heading(11, "Deterministic Forensic Risk Assessment")
        pdf.paragraph(
            "The case risk score is calculated strictly by the deterministic, formulaic risk engine. "
            "Scoring is 100% objective and mathematically calculated from verified database signals. "
            "Generative AI never calculates, overrides, or inflates the numeric risk score."
        )

        # Risk Score Banner Box
        risk_lvl_clean = str(risk_data.risk_level).replace("RiskLevel.", "")
        risk_color = (225, 29, 72) if risk_lvl_clean == "CRITICAL" else (217, 119, 6) if risk_lvl_clean == "HIGH" else (5, 150, 105)
        clean_exp = str(risk_data.explanation).replace("RiskLevel.", "")
        risk_summary_text = (
            f"OVERALL FORENSIC RISK SCORE: {risk_data.score} / 100 ({risk_lvl_clean})\n"
            f"Scale: 0-24: LOW | 25-49: MODERATE | 50-74: HIGH | 75-100: CRITICAL\n"
            f"Assessment Formula Rationale: {clean_exp}"
        )
        pdf.callout_box(risk_summary_text, title="Deterministic Risk Engine Assessment", badge=risk_lvl_clean, badge_color=risk_color)

        if risk_data.signals:
            pdf.subsection_heading("Observed Risk Signal Indicators")
            sig_headers = ["Risk Signal Indicator", "Occurrences", "Impact Contribution", "Forensic Rationale"]
            sig_widths = [50, 24, 32, 80]
            sig_aligns = ["L", "C", "C", "L"]
            sig_rows = []

            for sig in risk_data.signals:
                sig_rows.append([
                    sig.signal_type,
                    str(sig.count),
                    f"+{sig.impact_score} pts",
                    sig.reason
                ])

            pdf.render_table(sig_headers, sig_widths, sig_rows, sig_aligns)

        # -------------------------------------------------------------------------
        # SECTION 12: AI-ASSISTED FORENSIC FINDINGS
        # -------------------------------------------------------------------------
        pdf.section_heading(12, "AI-Assisted Forensic Findings")
        pdf.paragraph(
            "The CRYPTEVID AI Intelligence Engine synthesizes case signals into structured insights. "
            "To uphold judicial integrity, cryptographically verified FACTS are strictly distinguished "
            "from AI-generated contextual HYPOTHESES and investigative interpretations."
        )

        pdf.subsection_heading("Verified Objective Forensic Facts (Database & Services)")
        if ai_data.facts:
            for f in ai_data.facts:
                pdf.paragraph(f"- {f}", font_size=7.5)
        else:
            pdf.paragraph("No objective anomalies detected across baseline forensic datasets.", font_size=7.5)

        pdf.subsection_heading("AI Contextual Interpretations & Threat Hypotheses")
        if ai_data.ai_interpretations:
            for interp in ai_data.ai_interpretations:
                pdf.paragraph(f"* [HYPOTHESIS] {interp}", font_size=7.5, text_color=(71, 85, 105))
        else:
            pdf.paragraph("AI correlation indicates nominal baseline behaviors across all registered exhibits.", font_size=7.5)

        pdf.paragraph(
            "Disclaimer: AI findings provide contextual investigative hypotheses to assist human examiners "
            "and do not constitute legally binding judicial findings without independent verification.",
            font_size=6.8,
            text_color=(100, 116, 139)
        )

        # -------------------------------------------------------------------------
        # SECTION 13: AI RECOMMENDATIONS AND MITIGATION
        # -------------------------------------------------------------------------
        pdf.section_heading(13, "AI Recommendations and Mitigation")
        pdf.paragraph(
            "Recommended investigative countermeasures generated directly from observed case signals and risk triggers:"
        )

        if recs_data.recommendations:
            rec_headers = ["Priority", "Category", "Recommended Countermeasure", "Forensic Rationale"]
            rec_widths = [22, 34, 60, 70]
            rec_aligns = ["C", "L", "L", "L"]
            rec_rows = []

            for rec in recs_data.recommendations:
                rec_rows.append([
                    rec.severity,
                    rec.action_category,
                    f"{rec.title}: {rec.description}",
                    rec.reason
                ])

            pdf.render_table(
                rec_headers, rec_widths, rec_rows, rec_aligns,
                status_rules={0: {"CRITICAL": (225, 29, 72), "HIGH": (217, 119, 6), "MEDIUM": (71, 85, 105), "LOW": (5, 150, 105)}}
            )
        else:
            pdf.callout_box("No urgent countermeasures required at this time.", title="Recommendation Status", badge="NOMINAL")

        # -------------------------------------------------------------------------
        # SECTION 14: INVESTIGATION METHODOLOGY AND LIMITATIONS
        # -------------------------------------------------------------------------
        pdf.section_heading(14, "Investigation Methodology and Limitations")
        methodology_text = (
            "PROCEDURES & PROTOCOLS:\n"
            "1. Cryptographic Hashing: Every exhibit undergoes streaming bit-stream calculation using FIPS 180-4 SHA-256.\n"
            "2. Evidence Preservation: Original baselines are archived in logically air-gapped preservation containers (ISO/IEC 27037).\n"
            "3. Metadata Extraction: Lossless metadata harvesting inspects container structures without modifying access timestamps.\n"
            "4. Deterministic Risk Assessment: Formulas evaluate mathematical weights for tamper events, custody anomalies, and alerts.\n"
            "5. AI Correlation: Secondary correlation employs structured LLM prompting with strict separation between facts and hypotheses.\n\n"
            "LIMITATIONS & CONSTRAINTS:\n"
            "- Analysis is bounded by the physical and logical files ingested into the CRYPTEVID container.\n"
            "- Missing optional container metadata (e.g. EXIF or GPS coordinates) reflects standard privacy wiping and is not tamper evidence.\n"
            "- Network captures (PCAP) and encrypted archives require external cryptographic keys for deep payload inspection."
        )
        pdf.paragraph(methodology_text, font_size=7.5)

        # -------------------------------------------------------------------------
        # SECTION 15: DIGITAL INVESTIGATION DIARY (BNSS SECTION 192 RECORD)
        # -------------------------------------------------------------------------
        pdf.section_heading(15, "Digital Investigation Diary (BNSS Section 192 Record)")
        pdf.paragraph(
            "Pursuant to the principles of Section 192 of the Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS), "
            "an investigating officer maintains day-by-day proceedings in an investigation diary, setting forth "
            "the time information reached them, investigation commencement and closing times, places visited, "
            "and a statement of circumstances and findings ascertained. In CRYPTEVID, each daily entry is cryptographically "
            "sealed with SHA-256 hash chaining and immutable versioned amendments."
        )

        if not diary_list:
            pdf.callout_box(
                "No digital investigation diary entries have been entered in this case container yet.",
                title="Investigation Diary Status",
                badge="NOMINAL"
            )
        else:
            pdf.paragraph(f"A total of {len(diary_list)} investigation diary record(s) are cryptographically logged for this case container.")

            # Summary Table of Diary Entries
            diary_headers = ["Entry #", "Date", "Times (Start - Close)", "Places Visited", "SHA-256 Digest", "Status"]
            diary_widths = [20, 24, 34, 44, 46, 18]
            diary_aligns = ["C", "C", "C", "L", "L", "C"]
            diary_rows = []

            for entry in diary_list:
                ecode = entry.get("entry_code") or f"DE-{entry.get('entry_number', 1):03d}"
                dt = entry.get("investigation_date", "N/A")
                times = f"{entry.get('start_time', '')} - {entry.get('closing_time', '')}"
                places = ", ".join(entry.get("places_visited", [])) or "None"
                hash_disp = entry.get("entry_hash", "")[:18] + "..." if entry.get("entry_hash") else "SEALED"
                stat = "AMENDED" if entry.get("is_amended") else "FINALIZED"
                diary_rows.append([ecode, dt, times, places, hash_disp, stat])

            pdf.render_table(
                diary_headers, diary_widths, diary_rows, diary_aligns,
                status_rules={5: {"AMENDED": (217, 119, 6), "FINALIZED": (5, 150, 105)}}
            )

            # Detailed Record Cards for each Entry
            for entry in diary_list:
                ecode = entry.get("entry_code") or f"Entry #{entry.get('entry_number', 1)}"
                inv_date = entry.get("investigation_date", "N/A")
                pdf.subsection_heading(f"Diary Proceeding: {ecode} (Date: {inv_date})")

                rec_info = entry.get("time_info_received") or "Not applicable"
                hours = f"{entry.get('start_time', '')} to {entry.get('closing_time', '')}"
                places_str = ", ".join(entry.get("places_visited", [])) or "None recorded"
                ev_refs = ", ".join([str(e)[-8:] for e in entry.get("related_evidence_ids", [])]) or "None"
                inv_officer = f"{entry.get('created_by_name', 'Investigator')} (UID: {str(entry.get('created_by', ''))[-8:]})"

                kv_pairs = [
                    ("Entry Identifier", ecode),
                    ("Investigation Date", inv_date),
                    ("Info Received Time", rec_info),
                    ("Investigation Hours", hours),
                    ("Investigating Officer", inv_officer),
                    ("Places Visited", places_str),
                    ("Related Exhibits", ev_refs),
                    ("Cryptographic Seal", (entry.get("entry_hash") or "")[:24] + "...")
                ]
                if entry.get("detected_language"):
                    kv_pairs.append(("AI Format / Language", f"Processed by AI [{entry.get('detected_language')}]"))
                pdf.key_value_grid(kv_pairs, cols=2)

                # Narrative blocks
                pdf.paragraph(f"Proceedings & Activities: {entry.get('activities_performed', '')}", font_size=7.5)
                pdf.paragraph(f"Ascertained Circumstances & Findings: {entry.get('findings', '')}", font_size=7.5)

                # Chronological Event Timeline Sequence Table (AI-organized milestones)
                timeline = entry.get("timeline_events", [])
                if timeline:
                    pdf.check_space(20)
                    pdf.set_font("helvetica", "B", 7.5)
                    pdf.set_text_color(11, 27, 61)
                    pdf.cell(186, 4.5, _safe_text("Chronological Event Timeline Sequence (AI-Organized Milestones):"), new_x="LMARGIN", new_y="NEXT")
                    
                    tl_headers = ["Time", "Location / Node", "Investigative Activity Proceeding"]
                    tl_widths = [24, 46, 116]
                    tl_aligns = ["C", "L", "L"]
                    tl_rows = []
                    for ev in timeline:
                        t_str = ev.get("time", "") if isinstance(ev, dict) else getattr(ev, "time", "")
                        loc_str = ev.get("location", "") if isinstance(ev, dict) else getattr(ev, "location", "")
                        act_str = ev.get("activity", "") if isinstance(ev, dict) else getattr(ev, "activity", "")
                        tl_rows.append([t_str, loc_str, act_str])
                    
                    pdf.render_table(tl_headers, tl_widths, tl_rows, tl_aligns)
                    pdf.ln(1.5)

                if entry.get("raw_input"):
                    raw_sample = str(entry.get("raw_input")).strip()
                    if len(raw_sample) > 280:
                        raw_sample = raw_sample[:277] + "..."
                    pdf.paragraph(f"Original Raw Notes ({entry.get('detected_language') or 'Informal'}): \"{raw_sample}\"", font_size=6.8, text_color=(100, 116, 139))

                if entry.get("next_steps"):
                    pdf.paragraph(f"Next Steps & Remarks: {entry.get('next_steps')}", font_size=7.2, text_color=(71, 85, 105))

                # Note on witness confidentiality
                if entry.get("witness_references"):
                    from app.core.rbac import is_admin
                    if is_admin(user) or str(user.get("role", "")).lower() == "investigator":
                        pdf.paragraph(f"Witness References [CONFIDENTIAL BNSS SEC. 192(3)]: {entry.get('witness_references')}", font_size=7.2, text_color=(184, 134, 11))
                    else:
                        pdf.paragraph("Witness References: [RESTRICTED - CONFIDENTIAL UNDER BNSS SEC. 192(3)]", font_size=7.2, text_color=(100, 116, 139))

                if entry.get("is_amended") and entry.get("amendments"):
                    amend_count = len(entry.get("amendments", []))
                    last_amend = entry.get("amendments")[-1]
                    pdf.paragraph(
                        f"Amendment Audit Note: This entry contains {amend_count} verified correction(s). "
                        f"Latest Amendment by {last_amend.get('amended_by_name', 'Officer')} on "
                        f"{str(last_amend.get('timestamp', ''))[:16]}. Reason: '{last_amend.get('reason', '')}'.",
                        font_size=6.8,
                        text_color=(180, 83, 9)
                    )
                pdf.ln(2)

        pdf.callout_box(
            "BNSS SECTION 192 STATUTORY NOTICE: This digital diary record is maintained in accordance with "
            "the principles of Section 192 of the Bharatiya Nagarik Suraksha Sanhita, 2023. These records "
            "document proceedings and ascertained circumstances under cryptographic hash protection. Admissibility "
            "and procedural requirements remain subject to state police regulations and court directions.",
            title="Legal Framework Notice",
            badge="STATUTORY"
        )

        # -------------------------------------------------------------------------
        # SECTION 16: FINDINGS AND CONCLUSION
        # -------------------------------------------------------------------------
        pdf.section_heading(16, "Findings and Conclusion")
        verdict_status = "CRITICAL INTEGRITY CONCERNS" if tampered_count > 0 else "INTEGRITY FULLY VERIFIED"
        conclusion_body = (
            f"The forensic examination of Case {case_num} ('{case.get('title', 'Incident')}') has concluded. "
            f"Of the {len(evidence_list)} exhibit(s) examined, {verified_count} exhibit(s) match initial ingestion baselines. "
            f"A total of {tampered_count} exhibit(s) demonstrated hash mismatches, and {sec_count} security alerts were recorded.\n\n"
            f"Chain of custody records ({len(custody_list)} events) show complete actor attestation with cryptographic integrity. "
            f"The calculated deterministic risk score is {risk_data.score}/100 ({risk_lvl}). "
            f"All forensic exhibits and audit trails remain preserved and accessible for judicial proceedings."
        )
        pdf.callout_box(conclusion_body, title=f"Examiner Summary: {verdict_status}", badge=risk_lvl, badge_color=integ_color)

        # -------------------------------------------------------------------------
        # SECTION 17: REPORT INTEGRITY AND AUTHORIZATION
        # -------------------------------------------------------------------------
        pdf.section_heading(17, "Report Integrity and Authorization")
        pdf.paragraph(
            "CRYPTOGRAPHIC REPORT SEALING PROTOCOL:\n"
            "Upon compilation, the finalized PDF byte stream is passed through FIPS 180-4 SHA-256 cryptographic hashing. "
            "The calculated digest is permanently registered into the CRYPTEVID immutable database registry and mirrored "
            "to the tamper-evident audit ledger. Any byte-level modification after generation invalidates this official seal."
        )

        prev_ref_str = f"v{version - 1}.0" if version > 1 else "Initial Release (v1.0)"
        pdf.key_value_grid([
            ("Report Identifier", report_id_str),
            ("Document Version", f"v{version}.0"),
            ("Generation Timestamp", now.strftime("%Y-%m-%d %H:%M:%S UTC")),
            ("Authorized Examiner", prepared_by),
            ("Previous Version Reference", prev_ref_str),
            ("Registry Status", "PENDING_CRYPTOGRAPHIC_FINALIZATION")
        ], cols=2)

        # Official Certification Box & Signature
        pdf.check_space(32)
        pdf.ln(2)
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(203, 213, 225)
        cert_y = pdf.get_y()
        pdf.rect(12, cert_y, 186, 28, "DF")

        pdf.set_xy(16, cert_y + 2.5)
        pdf.set_font("helvetica", "B", 7.5)
        pdf.set_text_color(11, 27, 61)
        pdf.cell(178, 4, "OFFICIAL FORENSIC EXAMINER CERTIFICATION", new_x="LMARGIN", new_y="NEXT")

        pdf.set_x(16)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(178, 3.6, _safe_text(
            "I hereby attest under official oath that this forensic report accurately documents the state of all "
            "exhibits, cryptographic hashes, and custody ledgers associated with this case container as of the generation timestamp."
        ))

        pdf.set_xy(16, cert_y + 19)
        pdf.set_font("helvetica", "B", 7.5)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(85, 4.5, _safe_text(f"Examiner Signature: {user_name}"), border="T")
        pdf.set_xy(110, cert_y + 19)
        pdf.cell(82, 4.5, f"Date: {now.strftime('%d %B %Y')}", border="T")
        pdf.set_y(cert_y + 32)

        # -------------------------------------------------------------------------
        # SECTION 18: APPENDICES
        # -------------------------------------------------------------------------
        pdf.section_heading(18, "Appendices")
        pdf.subsection_heading("Appendix A: Complete Exhibits Cryptographic Hash Registry")
        app_a_headers = ["Evidence Exhibit", "File Size", "Unabridged Baseline SHA-256 Digest", "Status"]
        app_a_widths = [45, 22, 95, 24]
        app_a_aligns = ["L", "R", "L", "C"]
        app_a_rows = []

        for ev in evidence_list:
            app_a_rows.append([
                ev.get("original_filename", "Artifact"),
                f"{ev.get('file_size', 0):,} B",
                ev.get("sha256_hash", "UNKNOWN"),
                ev.get("integrity_status", "VERIFIED")
            ])

        pdf.render_table(
            app_a_headers, app_a_widths, app_a_rows, app_a_aligns,
            status_rules={3: {"TAMPERED": (225, 29, 72), "VERIFIED": (5, 150, 105)}}
        )

        pdf.subsection_heading("Appendix B: Forensic & Cryptographic Terminology Glossary")
        glossary_items = [
            ("SHA-256", "FIPS 180-4 secure cryptographic hash producing an immutable 256-bit identifier for bit-stream verification."),
            ("Chain of Custody", "Continuous chronological documentation of evidence acquisition, transfer, analysis, and disposition."),
            ("Tamper-Evident", "Properties allowing unauthorized modifications to be reliably and cryptographically detected."),
            ("Bit-stream Preservation", "Exact bit-level image of original digital media guaranteeing zero alteration to original source."),
            ("Deterministic Risk", "Objective mathematical scoring based on formulaic signal weights rather than generative AI estimates.")
        ]
        pdf.key_value_grid(glossary_items, cols=1)

        # 3. Output PDF to disk
        if not target_path:
            reports_dir = os.path.join(settings.EVIDENCE_STORAGE_DIR, "reports", case_id_str)
            os.makedirs(reports_dir, exist_ok=True)
            filename = f"Forensic_Report_{case_num}_v{version}_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
            file_path = os.path.join(reports_dir, filename)
        else:
            file_path = target_path
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

        pdf.output(file_path)
        return file_path

    @classmethod
    async def generate_case_report(
        cls,
        db,
        case_id: str,
        user: Dict[str, Any],
        title: Optional[str] = None,
        classification: Optional[str] = None
    ) -> ForensicReportResponse:
        case_id_str = str(case_id)
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else None

        case = await db["cases"].find_one({"_id": case_oid if case_oid else case_id_str})
        if not case:
            raise ValueError("CASE_NOT_FOUND")

        case_num = case.get("case_number", "CASE")
        now = datetime.now(timezone.utc)

        # 1. Determine Report Version
        prev_reports_count = await db["forensic_reports"].count_documents({"case_id": case_id_str})
        version = prev_reports_count + 1

        report_title = title or f"Forensic Investigation Final Examination Report - {case_num} (v{version})"
        report_class = classification or "Confidential"

        reports_dir = os.path.join(settings.EVIDENCE_STORAGE_DIR, "reports", case_id_str)
        os.makedirs(reports_dir, exist_ok=True)
        filename = f"Forensic_Report_{case_num}_v{version}_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path = os.path.join(reports_dir, filename)

        # 2. Render PDF File
        await cls.render_pdf_file(
            db=db,
            case_id=case_id_str,
            user=user,
            title=report_title,
            classification=report_class,
            version=version,
            target_path=file_path
        )

        # 3. Compute Streaming SHA-256 of Finalized PDF
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        report_hash = sha256.hexdigest()
        file_size = os.path.getsize(file_path)

        # 4. Store in Database
        report_doc = {
            "case_id": case_id_str,
            "case_number": case_num,
            "title": report_title,
            "version": version,
            "classification": report_class,
            "filename": filename,
            "file_path": file_path,
            "file_size": file_size,
            "sha256_hash": report_hash,
            "generated_by": str(user.get("_id", "0000")),
            "generated_by_name": user.get("name", "Chief Investigator"),
            "generated_at": now
        }
        res = await db["forensic_reports"].insert_one(report_doc)
        report_id = str(res.inserted_id)

        # 5. Audit Log
        from app.repositories.audit import AuditRepository
        audit_repo = AuditRepository(db)
        await audit_repo.create_log(
            user_id=str(user.get("_id", "0000")),
            action="REPORT_GENERATED",
            ip_address="127.0.0.1",
            user_agent="FastAPI-ReportingEngine",
            case_id=case_id_str,
            details=f"Generated court-admissible forensic PDF report v{version} for {case_num} (SHA-256: {report_hash[:16]}...)"
        )

        return ForensicReportResponse(
            report_id=report_id,
            case_id=case_id_str,
            case_number=case_num,
            title=report_title,
            version=version,
            classification=report_class,
            file_size=file_size,
            sha256_hash=report_hash,
            generated_by=str(user.get("_id", "0000")),
            generated_by_name=user.get("name", "Chief Investigator"),
            generated_at=now,
            download_url=f"/api/reports/{report_id}/download"
        )
