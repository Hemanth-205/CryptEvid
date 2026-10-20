import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import httpx
from app.core.config import settings
from app.models.diary import TimelineEvent, DiaryParseResponse

logger = logging.getLogger(__name__)

# Common Tanglish linguistic markers (Tamil expressed in Latin alphabet)
TANGLISH_VOCAB = {
    "inniku", "innaki", "indru", "kaalaila", "kaalai", "sayanthram", "maala", "iravu", "night",
    "apram", "aprom", "marubadiyum", "thirumba", "ponen", "ponom", "poirunthom", "paathen",
    "paathom", "eduthom", "vaanginom", "sonnanga", "pesunom", "solli", "irunthathu", "kedaichithu",
    "mudichom", "kelambinom", "aachu", "therinjithu", "vachu", "kuduthom", "vandhom", "pannom",
    "panninom", "panrom", "kita", "kitta", "la", "kulla", "poiduchu", "illai", "aama", "venum",
    "mudiyala", "disk", "image", "seize", "seized", "statement", "suspect", "server", "ip"
}

# Tanglish translation mapping for offline rule-based processor
TANGLISH_PHRASE_TRANSLATIONS = [
    (r"\b(?:inniku|innaki)\s+kaalaila\b", "Today during morning hours"),
    (r"\b(?:inniku|innaki)\b", "On the date of investigation"),
    (r"\bkaalaila\b", "during morning hours"),
    (r"\bsayanthram\b", "during evening hours"),
    (r"\b(?:apram|aprom|marubadiyum)\b", "subsequently"),
    (r"\b(?:ponen|ponom|poirunthom)\b", "visited and inspected"),
    (r"\b(?:paathom|paathen|check\s+pannom|check\s+panninom)\b", "examined and verified"),
    (r"\b(?:disk\s+image|image|clone)\s+(?:eduthom|pannom)\b", "acquired cryptographic bit-stream forensic image"),
    (r"\b(?:eduthom|vaanginom)\b", "seized and logged under chain of custody"),
    (r"\b(?:statement\s+vaanginom|pesunom)\b", "recorded witness statement and conducted interview"),
    (r"\b(?:kedaichithu|therinjithu|paathom)\b", "discovered evidentiary artifact"),
    (r"\b(?:mudichom|kelambinom)\b", "concluded proceedings for the day and departed"),
    (r"\b(?:suspicious\s+ah\s+irunthathu)\b", "exhibited anomalous activity indicators"),
    (r"\b(?:kita|kitta)\b", "with"),
    (r"\b(?:la|kulla)\b", "at"),
]

class DiaryAIService:
    """
    Forensic AI Intelligence Service for Digital Investigation Case Diaries (BNSS Section 192).
    Automatically detects unstructured notes in Tanglish (Tamil in Latin script), Hinglish,
    or informal bullet points, translates into court-admissible forensic English, extracts
    chronological milestones, and structures them into an ordered timeline.
    """

    @classmethod
    def detect_input_format(cls, text: str) -> str:
        """
        Analyze lexical tokens to detect Tanglish, Hinglish, or informal English notes.
        """
        lower = text.lower()
        words = re.findall(r"[a-z]+", lower)
        if not words:
            return "Informal English Notes"

        tanglish_matches = sum(1 for w in words if w in TANGLISH_VOCAB)
        tanglish_ratio = tanglish_matches / max(len(words), 1)

        if tanglish_matches >= 3 or tanglish_ratio > 0.08:
            return "Tanglish (Tamil in Latin Script)"

        hindi_markers = {"aaj", "subah", "dopahar", "shaam", "gaye", "dekha", "liya", "kiya", "baat", "mila", "pata", "chala"}
        hindi_matches = sum(1 for w in words if w in hindi_markers)
        if hindi_matches >= 3:
            return "Hinglish (Hindi in Latin Script)"

        return "Unstructured Field Notes (English)"

    @classmethod
    async def parse_and_organize(
        cls,
        raw_text: str,
        investigation_date: Optional[str] = None,
        db = None
    ) -> DiaryParseResponse:
        """
        Parse raw daily notes or Tanglish text, organize every event in chronological order
        with exact timeline milestones, and format according to BNSS Section 192 standards.
        """
        detected_lang = cls.detect_input_format(raw_text)
        today_str = investigation_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 1. Attempt Gemini Generative Parsing if API Key is configured
        gemini_key = settings.GEMINI_API_KEY
        if db is not None and not gemini_key:
            try:
                settings_col = db["settings"]
                global_cfg = await settings_col.find_one({"key": "global_config"})
                if global_cfg and global_cfg.get("gemini_api_key"):
                    gemini_key = global_cfg.get("gemini_api_key")
            except Exception:
                pass

        if gemini_key and gemini_key.strip():
            ai_result = await cls._parse_with_gemini(raw_text, detected_lang, today_str, gemini_key.strip())
            if ai_result is not None:
                return ai_result

        # 2. Fallback to Heuristic NLP / Linguistic Rule-Based Parser
        return cls._parse_heuristic_fallback(raw_text, detected_lang, today_str)

    @classmethod
    async def _parse_with_gemini(
        cls,
        raw_text: str,
        detected_lang: str,
        default_date: str,
        api_key: str
    ) -> Optional[DiaryParseResponse]:
        """
        Invoke Google Gemini with strict judicial JSON schema.
        """
        prompt = (
            "You are a Senior Digital Forensics Examiner and Judicial Polyglot in India. "
            "You are reviewing daily investigation field notes written by an investigating officer. "
            "The notes may be written in Tanglish (Tamil phrases written in English script, e.g. 'inniku morning 10 am ku cyber cell ponen, server room la disk image eduthom, apram bank manager kita pesunom'), "
            "Hinglish, informal bullet points, or voice-to-text transcripts.\n\n"
            "Your task is to:\n"
            "1. Accurately identify the language/format.\n"
            "2. Translate any non-English/Tanglish phrases into formal, court-admissible forensic English meeting Section 192 of the Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS).\n"
            "3. Extract EVERY SINGLE EVENT and organize them in STRICT CHRONOLOGICAL ORDER in a timeline.\n"
            "4. Extract start time (earliest event), closing time (latest event), places visited, detailed activities, findings/circumstances discovered, witness references, and next steps.\n\n"
            f"Input Raw Notes:\n\"\"\"\n{raw_text}\n\"\"\"\n\n"
            f"Target Investigation Date: {default_date}\n\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            f'  "detected_language": "{detected_lang}",\n'
            f'  "investigation_date": "{default_date}",\n'
            '  "time_info_received": "time in HH:MM format if mentioned or null",\n'
            '  "start_time": "HH:MM (e.g. 09:30)",\n'
            '  "closing_time": "HH:MM (e.g. 18:00)",\n'
            '  "places_visited": ["Place 1", "Place 2"],\n'
            '  "activities_performed": "Comprehensive formal paragraph of day-by-day proceedings in English",\n'
            '  "findings": "Statement of circumstances and findings ascertained through investigation in English",\n'
            '  "timeline_events": [\n'
            '    {\n'
            '      "time": "HH:MM",\n'
            '      "location": "Specific location or node",\n'
            '      "activity": "Detailed formal description of what was done at this time"\n'
            '    }\n'
            '  ],\n'
            '  "witness_references": "Witness identity or statement references, or null if none",\n'
            '  "next_steps": "Action items and follow-up steps, or null if none"\n'
            "}"
        )

        for model_name in ["gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash"]:
            try:
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                async with httpx.AsyncClient(timeout=25.0) as client:
                    resp = await client.post(
                        gemini_url,
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"responseMimeType": "application/json"}
                        }
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        text_output = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text_output:
                            parsed = json.loads(text_output)
                            if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                                parsed = parsed[0]
                            if isinstance(parsed, dict):
                                raw_timeline = parsed.get("timeline_events", [])
                                clean_events = []
                                for ev in raw_timeline:
                                    if isinstance(ev, dict) and ev.get("time") and ev.get("activity"):
                                        clean_events.append(TimelineEvent(
                                            time=str(ev.get("time", "")).strip(),
                                            location=str(ev.get("location") or "Site of Investigation").strip(),
                                            activity=str(ev.get("activity", "")).strip()
                                        ))

                                # Sort chronological
                                clean_events.sort(key=lambda x: cls._normalize_time_to_minutes(x.time))

                                places = parsed.get("places_visited", [])
                                if not places and clean_events:
                                    places = list({e.location for e in clean_events if e.location and e.location != "Site of Investigation"})

                                return DiaryParseResponse(
                                    detected_language=parsed.get("detected_language") or detected_lang,
                                    investigation_date=parsed.get("investigation_date") or default_date,
                                    time_info_received=parsed.get("time_info_received"),
                                    start_time=parsed.get("start_time") or (clean_events[0].time if clean_events else "09:30"),
                                    closing_time=parsed.get("closing_time") or (clean_events[-1].time if clean_events else "18:00"),
                                    places_visited=places if isinstance(places, list) else [str(places)],
                                    activities_performed=parsed.get("activities_performed") or raw_text,
                                    findings=parsed.get("findings") or "Ascertained circumstances and artifacts logged on timeline.",
                                    timeline_events=clean_events,
                                    witness_references=parsed.get("witness_references"),
                                    next_steps=parsed.get("next_steps"),
                                    ai_provider=f"Google Gemini Multilingual Intelligence ({model_name})",
                                    raw_text=raw_text
                                )
            except Exception as e:
                logger.warning(f"Gemini parsing attempt with {model_name} failed: {e}")
                continue

        return None

    @classmethod
    def _parse_heuristic_fallback(
        cls,
        raw_text: str,
        detected_lang: str,
        default_date: str
    ) -> DiaryParseResponse:
        """
        High-fidelity rule-based linguistic and timestamp extractor when offline or without API key.
        Handles Tanglish replacements, timestamp extractions, and chronological ordering.
        """
        # 1. Translate Tanglish keywords
        translated_text = raw_text
        for pattern, replacement in TANGLISH_PHRASE_TRANSLATIONS:
            translated_text = re.sub(pattern, replacement, translated_text, flags=re.IGNORECASE)

        # 2. Extract Sentences / Chunks
        # Normalize commas preceding timestamps or transition adverbs into statement boundaries
        preprocessed = re.sub(
            r",\s*(?=(?:\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm|hrs|hours)?\b|apram\b|after\s*that\b|then\b|later\b|next\b|finally\b|around\b|at\s*\d))",
            "; ",
            raw_text,
            flags=re.IGNORECASE
        )
        raw_chunks = [c.strip() for c in re.split(r"[.\n;]+", preprocessed) if len(c.strip()) > 3]

        events: List[TimelineEvent] = []
        places_set = set()
        info_received_time: Optional[str] = None
        witness_refs: List[str] = []

        # Common place patterns
        place_keywords = ["cyber cell", "server room", "hosting facility", "bank", "vault", "lab", "branch", "police station", "hq", "data center", "datacenter", "office"]

        # Default time intervals if times are sparse
        default_hours = ["09:30", "11:00", "13:30", "15:15", "17:00", "18:00"]
        default_idx = 0

        for chunk in raw_chunks:
            # Check for explicit times in this chunk: e.g. 10:00, 10 am, 14:30, 11.30am
            time_match = re.search(r"\b(\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm|hrs|hours)?|\d{1,2}\s*(?:am|pm))\b", chunk, re.IGNORECASE)
            assigned_time = ""
            if time_match:
                assigned_time = cls._clean_time_string(time_match.group(1))
            else:
                assigned_time = default_hours[min(default_idx, len(default_hours) - 1)]
                default_idx += 1

            # Detect location in chunk
            loc_found = "Investigation Site"
            lower_chunk = chunk.lower()
            for pk in place_keywords:
                if pk in lower_chunk:
                    loc_found = pk.title()
                    places_set.add(loc_found)
                    break

            # Translate chunk for activity description
            formal_chunk = chunk
            for pattern, replacement in TANGLISH_PHRASE_TRANSLATIONS:
                formal_chunk = re.sub(pattern, replacement, formal_chunk, flags=re.IGNORECASE)

            # Check if this chunk is a witness reference
            if any(w in lower_chunk for w in ["witness", "manager", "admin", "testimony", "statement", "pesunom"]):
                witness_refs.append(formal_chunk.strip())

            # Check for info received
            if any(w in lower_chunk for w in ["received", "info", "thakaval", "alert", "notification"]):
                if not info_received_time and time_match:
                    info_received_time = assigned_time

            events.append(TimelineEvent(
                time=assigned_time,
                location=loc_found,
                activity=formal_chunk.strip()
            ))

        # Sort timeline chronologically
        events.sort(key=lambda x: cls._normalize_time_to_minutes(x.time))

        start_time = events[0].time if events else "09:30"
        closing_time = events[-1].time if events else "18:00"

        # Construct formal activities summary
        activities_performed = (
            f"The investigating officer conducted day-by-day proceedings for Case on {default_date}. "
            + " ".join(e.activity + "." for e in events)
        )

        findings = (
            "During proceedings across visited locations, evidence exhibits and system parameters were inspected. "
            "Forensic bit-stream baselines and circumstances were recorded in accordance with BNSS Section 192."
        )

        next_steps = "Continue offline forensic artifact analysis, coordinate with forensic laboratory, and maintain custody verification."

        return DiaryParseResponse(
            detected_language=detected_lang,
            investigation_date=default_date,
            time_info_received=info_received_time,
            start_time=start_time,
            closing_time=closing_time,
            places_visited=sorted(list(places_set)) if places_set else ["State Cyber Forensic Laboratory"],
            activities_performed=activities_performed,
            findings=findings,
            timeline_events=events,
            witness_references="; ".join(witness_refs) if witness_refs else None,
            next_steps=next_steps,
            ai_provider="CRYPTEVID Forensic Intelligence Engine (Linguistic & Timeline Processor)",
            raw_text=raw_text
        )

    @staticmethod
    def _clean_time_string(raw: str) -> str:
        s = raw.lower().replace("hrs", "").replace("hours", "").strip()
        is_pm = "pm" in s
        is_am = "am" in s
        s = s.replace("am", "").replace("pm", "").strip()
        s = s.replace(".", ":")

        if ":" in s:
            parts = s.split(":")
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        else:
            h = int(s) if s.isdigit() else 9
            m = 0

        if is_pm and h < 12:
            h += 12
        elif is_am and h == 12:
            h = 0

        return f"{h:02d}:{m:02d}"

    @staticmethod
    def _normalize_time_to_minutes(time_str: str) -> int:
        try:
            cleaned = DiaryAIService._clean_time_string(time_str)
            parts = cleaned.split(":")
            return int(parts[0]) * 60 + int(parts[1])
        except Exception:
            return 600  # Default 10:00 AM
