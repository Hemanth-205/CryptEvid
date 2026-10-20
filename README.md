# CRYPTEVID — Secure Digital Evidence & Forensic Intelligence Platform

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2019-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/Language-TypeScript-3178C6.svg?style=flat&logo=typescript)](https://www.typescriptlang.org/)
[![MongoDB](https://img.shields.io/badge/Database-MongoDB-47A248.svg?style=flat&logo=mongodb)](https://www.mongodb.com/)
[![TailwindCSS](https://img.shields.io/badge/Styling-TailwindCSS%20v4-38B2AC.svg?style=flat&logo=tailwind-css)](https://tailwindcss.com/)

**CRYPTEVID** is an enterprise-grade digital forensics, chain of custody, and forensic evidence analysis platform. It provides end-to-end cryptographic verification, multi-source timeline correlation, interactive evidence graphing, automated threat intelligence, and court-admissible forensic reporting for digital investigation teams and IoT-connected forensic ingestion hardware.

---

## Key Features

- **Evidence Vault & Cryptographic Integrity**:
  - SHA-256 bit-stream baseline verification on ingestion.
  - Real-time tamper detection identifying bit drift and file alterations.
  - Dual-copy preservation mechanism keeping original tamper-proof evidence intact.
- **Hardware-Integrated Multi-Factor Authentication**:
  - Role-based Access Control (RBAC: Admin, Investigator, Read-Only Auditor).
  - ESP32 hardware terminal integration with simulated or physical RFID card swipes and biometric fingerprint scans.
  - Heartbeat monitor and automatic offline failover for IoT ingestion nodes.
- **Immutable Chain of Custody**:
  - Cryptographically verifiable ledger tracking every upload, view, verification, transfer, and export.
  - Forensic actor, timestamp, IP address, and hardware node attribution.
- **Multi-Source Timeline Correlation Engine**:
  - Unifies network logs, RFID access events, SIEM alerts, and manual investigator notes into chronological order with confidence and precision scoring.
- **Interactive Evidence Topology Graph**:
  - Visual node-link mapping of cases, suspects, physical workstations, IoT taps, evidence files, and network activity.
- **AI Threat Intelligence & Risk Scoring**:
  - Deterministic risk assessment (0-100 scale).
  - Integrated Google Gemini AI reasoning separating verifiable forensic facts from hypothesis interpretations.
- **Court-Admissible PDF Reports**:
  - Automated PDF report compilation with embedded evidence tables, integrity seals, chain of custody logs, and investigator sign-offs.

---

## Architecture

```
Macro/
├── client/                     # Frontend Application (React 19 + TypeScript + Vite)
│   ├── src/
│   │   ├── components/         # Reusable UI components & navigation
│   │   ├── context/            # Auth, Theme, & WebSocket contexts
│   │   ├── pages/              # Dashboard, Vault, Timeline, Graph, Reports, Settings
│   │   ├── services/           # Axios API services
│   │   └── types/              # TypeScript interfaces & models
│   ├── package.json
│   └── vite.config.ts
├── server/                     # Backend Application (FastAPI + MongoDB)
│   ├── app/
│   │   ├── core/               # Security, DB connection, settings, WS manager
│   │   ├── models/             # Pydantic schemas & document models
│   │   ├── repositories/       # MongoDB data access layer
│   │   ├── routers/            # API endpoints (Auth, Cases, Evidence, Events, etc.)
│   │   └── services/           # Hashing, Custody, Graph, AI, PDF Report generation
│   ├── requirements.txt
│   └── seed_demo_case.py       # Comprehensive demo seed data script
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python**: 3.11+
- **Node.js**: 18+ (Node 20+ recommended) & npm
- **MongoDB**: Local MongoDB community service running on port 27017 or MongoDB Atlas connection URI

---

### Backend Setup

1. **Navigate to the server directory**:
   ```bash
   cd server
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**:
   Copy `.env.example` to `.env` and configure your settings:
   ```bash
   cp .env.example .env
   ```
   *Key variables*:
   ```env
   PROJECT_NAME=Secure Forensic IoT Platform
   MONGODB_URL=mongodb://localhost:27017
   DATABASE_NAME=macro
   JWT_SECRET_KEY=supersecretkey_change_in_production
   GEMINI_API_KEY=your_gemini_api_key_here
   SIMULATION_MODE=true
   HOST=127.0.0.1
   PORT=8000
   ```

5. **Seed Demo Investigation Case**:
   ```bash
   python seed_demo_case.py
   ```

6. **Start the FastAPI Server**:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   - API Server: `http://127.0.0.1:8000`
   - Interactive Swagger API Documentation: `http://127.0.0.1:8000/docs`

---

### Frontend Setup

1. **Navigate to the client directory**:
   ```bash
   cd ../client
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Environment Configuration**:
   Ensure `.env` contains:
   ```env
   VITE_API_URL=http://localhost:8000
   ```

4. **Start the Vite development server**:
   ```bash
   npm run dev
   ```
   - Web Application: `http://127.0.0.1:5173`

---

## Demo Accounts & Hardware Credentials

The database automatically initializes default roles and simulated hardware credentials:

| Role | Email | Password | RFID Badge UID | Fingerprint ID |
| :--- | :--- | :--- | :--- | :--- |
| **Administrator** | `admin@forensics.gov` | `password123` / `admin123` | `04A1B2C3` | `12` |
| **Investigator** | `investigator@forensics.gov` | `password123` | `B1C2D3E4` | `15` |
| **Auditor (Read-Only)** | `viewer@forensics.gov` | `password123` | `C3D4E5F6` | `20` |

---

## Automated Verification & Testing

To run the complete end-to-end verification suite:
```bash
cd server
python test_end_to_end_verification.py
```
This tests:
- Authentication, JWT issuance, & role checks
- Hardware simulation (RFID & Biometrics)
- Case management & note appending
- Ingestion, SHA-256 calculation, and tamper detection
- Timeline correlation & evidence topology graphs
- Deterministic risk scoring & AI threat reasoning
- PDF report compilation and cryptographic seal verification
- Real-time WebSocket bidirectional ping/pong

---

## License

This project is licensed under the MIT License.
