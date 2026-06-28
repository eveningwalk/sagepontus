# Sage Pontus

**AI-powered Red Flag screening and SOAP automation for Physical Therapists — delivered as a Chrome Extension.**

Live demo: [pt.sagepontus.com](https://pt.sagepontus.com)

---

## The Problem

The US physical therapy market is facing a structural liability crisis.

- **Direct Access** laws now let patients see PTs without a physician referral, making PTs the first-line screeners for serious pathology.
- A national **PTA shortage** forces clinics to maximize the use of Physical Therapist Assistants — who have less training in differential diagnosis.
- A missed red flag (undetected cancer, spinal fracture, cauda equina syndrome) triggers **multi-million dollar malpractice suits**.
- PTAs document 6–12 SOAP notes per day. Every note is a liability exposure point. None have systematic screening tools.

---

## The Product

A Chrome Extension that sits on top of any existing EMR (WebPT, Clinicient, etc.) — no switching cost, no double entry.

**Hook (for PTAs):** AI SOAP note automation. Reduces per-note documentation time from ~1 minute to ~10 seconds. Daily-use lock-in.

**Killer (for clinic directors):** Real-time Red Flag alarm + physician referral letter generator. Prevents lawsuits. The clinic director pays; the PTAs use it.

---

## What's Built

### Core Engine (`vertical_pt/engine/`)

| Module | Role |
|---|---|
| `vpps.py` | VPPA — unstructured SOAP text → symptom fact JSON. Rule-based matching (KB synonym + regex), AI fallback. Negation handling ("denies weight loss" excluded). |
| `scorer.py` | Maps VPPS hits to RED / YELLOW / NONE alarm via 8 clinical protocols (Goodman's guidelines). Logic variants: `WEIGHTED_SUM`, `ANY_CARDINAL`, `SCREEN_OF_5`. |
| `cra.py` | CRA — builds time-series patient context from session history. Detects `escalating` / `stable` / `improving` trends across up to 12 sessions. |
| `soap_extractor.py` | Extracts structured clinical context JSON from SOAP text (VAS, ROM, MMT, neurological findings, goals). Temperature=0, no inference. |
| `referral.py` | Generates physician referral letters. Cites APTA Clinical Practice Guidelines (RAG-backed, not hallucinated). |
| `rag.py` | pgvector + Gemini Embedding retrieval. APTA CPG chunks indexed for guideline citation in referral letters. |
| `integrity.py` | SHA-256 tamper-evident seal per session record. Legal auditability. |
| `scribe.py` | Audio transcription (AssemblyAI Medical API). Speaker-separated S/O section pre-fill. |

### Clinical Knowledge Base (`data/red_flag_protocols/`)

8 protocol files derived from Goodman & Snyder's *Differential Diagnosis for Physical Therapists*:

`cauda_equina` · `fracture` · `malignancy` · `vascular` · `infection` · `inflammatory` · `yellow_flag` · pathological fracture (composite rule)

### Chrome Extension (`chrome_extension/`)

Shadow DOM floating panel — overlays any EMR without page conflicts. SOAP paste → instant Red Flag analysis → referral letter in one flow. Auth via Django token, patient data stored locally (`chrome.storage.local` — no PHI on server).

### Test Coverage (`vertical_pt/tests/`)

29 scenario-based integration tests across all 8 conditions (RED / YELLOW / NONE). Real-world SOAP note validation against MTSamples, PMC case reports, and PT Reddit anonymized cases.

---

## Architecture

```
Chrome Extension (content.js)
        │  SOAP text + patient_id
        ▼
Django REST API  (/api/pt/analyze/)
        │
        ├── VPPS  →  Scorer  →  RED/YELLOW/NONE alarm
        │                  ↓
        │           CRA (session history trend)
        │                  ↓
        │           Referral letter (RAG: APTA CPG)
        │
        └── PatientTimeline (PostgreSQL + pgvector)
                   ↓
            AuditPair (clinician corrections → data moat)

Landing page: Next.js (sagepontus.com)
Backend:      Django + Gunicorn (pt.sagepontus.com, Cloud Run)
DB:           PostgreSQL / Cloud SQL
```

---

## Data Moat

Every time a clinician corrects an AI output — SOAP draft, alarm decision, referral letter — the delta is stored as a `(original, edited)` pair in `AuditPair`. This paired dataset:

- Personalizes alarm weight thresholds per clinic over time
- Cannot be replicated by a competitor without equivalent clinical usage time
- Feeds a reinforcement loop: more corrections → better accuracy → more trust → more corrections

---

## Quick Start

```bash
# 1. Clone and set up environment
git clone https://github.com/eveningwalk/sagepontus.git
cd sagepontus
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Fill in: DJANGO_SECRET_KEY, DATABASE_URL, GEMINI_API_KEY

# 3. Run migrations and seed Red Flag protocols
python manage.py migrate
python manage.py seed_red_flag
python manage.py seed_cpg        # APTA CPG chunks for RAG

# 4. Start
python manage.py runserver
```

**Run tests:**
```bash
pytest vertical_pt/tests/ -v
```

**Deploy:**
```bash
./deploy.sh   # runs pytest → gcloud run deploy
```

---

## Roadmap

| Phase | Feature | Status |
|---|---|---|
| 1–6 | Red Flag engine + Chrome Extension + Landing page | **Shipped** |
| 7 | Audit Loop — paired data collection (SOAP / alarm / document corrections) | **Shipped** |
| 8 | Temporal Red Flag — CRA→scorer trend integration, false-recovery alerts | Planned |
| 9 | Treatment Response Tracking — VAS/ROM session-over-session, stagnation alarms | Planned |
| 10 | Clinic Analytics Dashboard — referral accuracy, recovery curves, lawsuit ROI | Planned |
| 11 | PT Community — anonymized Red Flag case feed, members-only | Planned |
| Next | Patient Record Summarizer — multimodal (MRI, surgical notes) + provenance tracking | Roadmap |

---

## Stack

- **Backend:** Django 4.x, Django REST Framework, PostgreSQL, pgvector
- **AI:** Gemini 2.5 Flash (clinical context extraction), Gemini Embedding 001 (RAG), AssemblyAI Medical (audio)
- **Frontend:** Next.js 14 (landing), Chrome Extension MV3
- **Infra:** Google Cloud Run, Cloud SQL, Cloud Build
