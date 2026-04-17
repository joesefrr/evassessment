# Address Book API

This is a FastAPI application for managing addresses in SQLite.

It supports:
- create, list, get, update, and delete address records
- nearby search using latitude/longitude + distance in kilometers
- request logging to console and daily log files (`logs/YYYY-MM-DD.log`)

## Run in shell (local Python)

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the API:

```bash
uvicorn app.main:app --reload
```

4. Open docs:

`http://127.0.0.1:8000/docs`

## Run with Docker Compose (Recommended)

Build and start:

```bash
docker compose up --build
```

Stop:

```bash
docker compose down
```

API docs:

`http://127.0.0.1:8000/docs`
