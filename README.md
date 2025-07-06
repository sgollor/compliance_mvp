# compliance_mvp
Python MVP for compliance validation in Nigeria’s fintech and agent banking sector. Enables file upload, data validation, and real-time flagging of KYC/AML risks.

# Compliance MVP for Banking & Fintech Agents (Nigeria)

A lightweight Python-based MVP that allows independent banking/fintech agents to upload, validate, and flag compliance-related transaction data.

## What It Does

- ✅ Accepts `.csv` uploads from agents
- ✅ Validates required fields and data types
- ✅ Flags suspicious transactions and expired KYC
- ✅ Designed to simplify AML/KYC compliance for Nigeria’s agent networks

## Who It’s For

- **Fintech compliance officers**: monitor agent KYC/AML status
- **Banking agents**: self-check and update customer compliance data
- **Regulators (future)**: access summary reports and audit trails
- **Open-source contributors**: improve testing, docs, UI, and automation

## 🛠 Tech Stack

- Python (Flask, Pandas)
- SQLite or PostgreSQL
- Jinja Templates (HTML)
- ReportLab (PDF reports – coming soon)

## 📁 Folder Structure

compliance_mvp/
├── app.py # Flask backend
├── templates/
│ └── upload.html # Frontend upload form
├── uploads/ # Uploaded CSVs
├── .gitignore
└── README.md


## Required CSV Format

The uploaded file must include:

| Column       | Description                       |
|--------------|------------------------------------|
| agent_id     | Unique agent identifier            |
| agent_name   | Agent’s full name                  |
| kyc_status   | complete, incomplete, or expired   |
| id_expiry    | Date of KYC ID expiry              |
| txn_amount   | Transaction amount (numbers only)  |
| txn_time     | Date and time of transaction       |

## Future Tasks

- Add audit logs and report generation
- Add role-based login and dashboard
- Integrate with NIBSS or third-party KYC APIs

## Setup Instructions

```bash
git clone https://github.com/sgollor/compliance_mvp.git
cd compliance_mvp
pip install -r requirements.txt
python app.py
