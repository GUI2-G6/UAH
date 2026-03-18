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