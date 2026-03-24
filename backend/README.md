# UAH Backend - Local Development Guide

This guide explains how to run the FastAPI backend locally for testing purposes on your own machine. We use a separate `docker-compose` file just for spinning up a local PostgreSQL database, then run the Python app directly on your host machine to make debugging easy.

**Note:** This setup will run the database on your local machine and will not touch or break the dev server infrastructure.

## Prerequisites
- [Docker](https://www.docker.com/) installed and running.
- [Python 3.10+](https://www.python.org/downloads/) installed.

## Step 1: Start the Local Database

From the **root of the repository** (where the `docker-compose.local.yml` file is located), start the PostgreSQL container:

```bash
docker compose -f docker-compose.local.yml up -d
```

This will automatically create a database container running on `localhost:5432` with the correct default user, password, and database variables.

## Step 2: Set Up Python Virtual Environment

Navigate into the `backend/` directory from a terminal and create a virtual environment:

### On Windows (PowerShell/CMD):
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
```

### On Mac/Linux:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

## Step 3: Install Dependencies

With the virtual environment activated, install the backend libraries:
```bash
pip install -r requirements.txt
```

## Step 4: Run the Backend

Before running the FastAPI server, you need to map PostgreSQL's host to `localhost` so Python knows where to find the database container you started in Step 1.

### On Windows (PowerShell):
```powershell
$env:POSTGRES_HOST="localhost"
uvicorn app.main:app --reload
```

### On Mac/Linux:
```bash
POSTGRES_HOST=localhost uvicorn app.main:app --reload
```

## Step 5: Test the API

Open your browser and navigate to the Swagger UI:
- **API Sandbox:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Check Status:** [http://localhost:8000/](http://localhost:8000/)

## Teardown

To shut down the backend, press `Ctrl + C` in the terminal where `uvicorn` is running.

To shut down the local database:
```bash
# From the root of the repository
docker compose -f docker-compose.local.yml down
```

## Email Verification / Password Reset (Google Workspace)

Right now, the API endpoints for email verification and password reset generate JWT tokens.

- If `EMAILS_ENABLED=false` (default), the backend returns the token in the API response ("dev only") so you can test locally.
- If `EMAILS_ENABLED=true`, the backend will email the token using SMTP.

### Option A (simplest): Gmail SMTP with an App Password

1. Pick a real mailbox like `noreply@uahapp.com` (or `security@uahapp.com`).
2. Enable 2‑Step Verification on that mailbox.
3. Create an App Password (Google Account → Security → App passwords).
4. Set these env vars for the backend:

```powershell
$env:EMAILS_ENABLED="true"
$env:PUBLIC_APP_URL="https://uahapp.com"

$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USE_TLS="true"
$env:SMTP_USERNAME="noreply@uahapp.com"
$env:SMTP_PASSWORD="<APP_PASSWORD>"
$env:SMTP_FROM="UAH <noreply@uahapp.com>"
```

### Option B (production-friendly): Google Workspace SMTP relay

If you don’t want to store a mailbox password on the server, set up an SMTP relay in Google Admin:

- Admin console → Apps → Google Workspace → Gmail → Routing → SMTP relay service
- Allow your backend server IP(s) to relay
- Require TLS
- Restrict sender domain to `uahapp.com`

Then configure the backend with `SMTP_HOST="smtp-relay.gmail.com"` (port 587) and either:
- no auth (IP allowlist), or
- SMTP auth (depending on your relay configuration)

### Deliverability (recommended)

For best results, ensure your DNS has:
- SPF including Google (`include:_spf.google.com`)
- DKIM enabled in Google Admin and published to DNS
- A basic DMARC record