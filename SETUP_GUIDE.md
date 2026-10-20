# CRYPTEVID — Quick Setup & Running Guide for Teammates

This guide provides step-by-step instructions to set up and run the **CRYPTEVID Secure Digital Evidence & Forensic Intelligence Platform** on your local machine.

---

## 1. Prerequisites

Ensure you have the following installed on your machine:
- **Node.js**: v18+ or v20+ (Download from [nodejs.org](https://nodejs.org/))
- **Python**: v3.10, v3.11, or v3.12 (Download from [python.org](https://www.python.org/))
- **MongoDB**: Community Edition running locally on default port `27017` (Download from [mongodb.com](https://www.mongodb.com/try/download/community))

---

## 2. Project Architecture

The project is structured as a clean full-stack monorepo:
```text
CRYPTEVID/
├── client/              # React 19 + TypeScript + Vite + Tailwind CSS frontend
│   ├── src/             # Pages, components, hooks, and services
│   └── public/          # Branding assets and logo
├── server/              # FastAPI + Motor (Async MongoDB) + FPDF2 forensic backend
│   ├── app/             # Routers, services, models, and repositories
│   ├── static/          # PDF report templates and logos
│   └── requirements.txt # Python dependencies
└── SETUP_GUIDE.md       # This file
```

---

## 3. Backend Setup & Startup (FastAPI)

1. Open a terminal and navigate to the `server` directory:
   ```bash
   cd server
   ```

2. Create a virtual environment:
   - **Windows:**
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. *(Optional)* Seed initial demo cases, evidence, and court reports:
   ```bash
   python seed_demo_case.py
   ```

5. Start the backend server:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

The backend API will be live at:
- **API Base:** `http://localhost:8000`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`

---

## 4. Frontend Setup & Startup (React + Vite)

1. Open a new terminal and navigate to the `client` directory:
   ```bash
   cd client
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

The web application will be accessible at:
- **Web App:** `http://localhost:5173/`

---

## 5. Default Login Credentials

Use any of the pre-configured forensic roles:

| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Chief Investigator / Admin** | `admin@forensics.gov` | `password123` | Full access (cases, evidence, reports, settings) |
| **Forensic Investigator** | `investigator@forensics.gov` | `password123` | Case management, evidence upload & verification |
| **Auditor / Viewer** | `viewer@forensics.gov` | `password123` | Read-only access to cases, reports, and ledgers |

---

## 6. Key Features Included

- **Forensic Command Center**: Live telemetry, risk posture, and evidence stats.
- **Evidence Vault**: Cryptographic SHA-256 intake, automated air-gapped preservation backups, and controlled tamper detection.
- **Chain of Custody Ledger**: ISO/IEC 27037 compliant immutable audit log with cryptographic hash chaining.
- **Evidence Relationship Graph**: Topological mapping connecting cases, exhibits, devices, and timeline events.
- **Deterministic Risk Scoring**: Formulaic 0–100 scoring (LOW, MODERATE, HIGH, CRITICAL).
- **Court-Admissible PDF Reports**: 17-section forensic dossier with dynamic cover page, sealed with a FIPS 180-4 SHA-256 post-generation hash.
- **Hardware Simulation & Device Management**: ESP32 RFID/fingerprint authentication with rogue device detection.
