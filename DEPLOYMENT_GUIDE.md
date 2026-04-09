# Deployment Guide — OutSystems Exam Simulator

## Overview — two environments, one codebase

`db.py` inspects the `DATABASE_URL` environment variable at startup and automatically picks the right database backend:

| Environment | Backend | Data persistence |
|---|---|---|
| **Local development** | SQLite (`users.db`) | Persists between runs; lost if file is deleted |
| **Replit (deployed)** | PostgreSQL | Fully persistent across all deployments |

No code changes are needed to switch between environments.

---

## Local Development

### Prerequisites
- Python 3.9+
- pip
- A modern browser

### Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set the required admin key
export GENERATE_API_KEY=dev-key-change-me   # Linux / macOS
set GENERATE_API_KEY=dev-key-change-me      # Windows

# 4. Start the app
python app.py
```

Open `http://localhost:5000`. The app creates `users.db` automatically on first run.

### What DATABASE_URL absent means
When `DATABASE_URL` is not set, `db.py` falls back to SQLite. The file `users.db` is created next to `app.py`. It is a local runtime file — do not commit it to source control (it is listed in `.gitignore`).

### Optional environment variables (local)

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | Enables AI batch generation and content verification |
| `OPENROUTER_MODEL` | Override the default AI model |

---

## Replit Deployment

### One-time Replit setup

1. **Open your Repl** in the Replit editor.

2. **Provision a PostgreSQL database** — go to the Database panel in the sidebar and click "Create Database". Replit sets `DATABASE_URL` automatically.

3. **Set required secrets** — go to Secrets (the padlock icon) and add:
   - `GENERATE_API_KEY` — any strong random string; used as the admin API key

4. **Optional secrets for AI features:**
   - `OPENROUTER_API_KEY`
   - `OPENROUTER_MODEL`

5. **Start the workflow** — the `Start application` workflow runs `python app.py`. Replit proxies port 5000 automatically.

6. **Deploy / publish** — click "Deploy" in the Replit toolbar. Each new deployment pulls fresh source code but connects to the same persistent PostgreSQL database. User accounts, attempt history, and exam results are never lost.

### How data survives deployments

Replit's deployment process rebuilds the project directory from source on every publish. Any file written at runtime (such as `users.db`) would be wiped. PostgreSQL is a **separate managed service** outside the project directory — it is not affected by deploys.

| Data type | Storage | Survives deploy? |
|---|---|---|
| User accounts + PINs | PostgreSQL | Yes |
| Exam attempts + results | PostgreSQL | Yes |
| Uploaded question batches | Object Storage | Yes |
| Built-in question batches | `questions/` directory (source code) | Yes |
| Flask sessions | Server memory | No — users must log in again |

### Scaling note
The app uses server-side Flask sessions (in-memory). If you scale to multiple workers or dynos, sessions will not be shared between processes. For multi-worker setups, configure a Redis-backed session store.

---

## Using PostgreSQL locally (optional)

If you want to use PostgreSQL locally instead of SQLite:

```bash
# Install and start PostgreSQL, then:
export DATABASE_URL=postgresql://user:password@localhost:5432/outsystems_exam

# Install psycopg2 (already in requirements.txt as psycopg2-binary)
pip install -r requirements.txt

python app.py
```

Tables are created automatically on first run via `init_db()`.

---

## Gunicorn (production WSGI server)

```bash
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

Use 1 worker per CPU core. Keep workers low if session state matters (see scaling note above).

---

## Environment variable reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Replit only | _(none — uses SQLite)_ | PostgreSQL connection string |
| `GENERATE_API_KEY` | **Yes** | _(none)_ | Admin key for batch generate/upload endpoints |
| `OPENROUTER_API_KEY` | Optional | _(none)_ | Enables AI features |
| `OPENROUTER_MODEL` | Optional | `google/gemma-4-31b-it:free` | AI model for generation |
| `REPLIT_OBJECT_STORAGE_BUCKET_ID` | Replit only | _(auto-detected)_ | Persists uploaded batches |

---

## Troubleshooting

### "relation does not exist" (PostgreSQL)
`init_db()` runs on startup and creates tables automatically. If you see this error, confirm `DATABASE_URL` is set correctly and the PostgreSQL service is running.

### SQLite data lost between runs
The `users.db` file must not be deleted between runs. Check it exists next to `app.py`. If you need durability on a server, switch to PostgreSQL by setting `DATABASE_URL`.

### Data lost after Replit deploy
Verify `DATABASE_URL` is set in the Replit Secrets panel (not a `.env` file). If it was unset, re-provision the database from the Replit Database panel.

### psycopg2 import error locally
`psycopg2-binary` is only imported when `DATABASE_URL` is set, so this error only appears if you set `DATABASE_URL` without installing the package:
```bash
pip install psycopg2-binary
```
