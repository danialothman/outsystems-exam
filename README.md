# OutSystems Exam Simulator

A Flask web application for practising OutSystems certification exams. Supports multiple users, attempt history with detailed question review, AI-generated question batches, and both local (SQLite) and Replit-hosted (PostgreSQL) deployments.

## Features

- **User accounts** — Register with a username and a 4–8 digit PIN; change PIN at any time. Accounts and data are kept indefinitely.
- **Practice exams** — Built-in question batch plus support for AI-generated or user-uploaded batches
- **Answer shuffling** — Option order is randomised per question but stays consistent within a session
- **Attempt history** — Every completed exam is saved; view score, pass/fail, and category breakdown
- **Detailed question review** — After an exam, filter questions by correct/incorrect and review explanations
- **AI content verification** — Uploaded batches are checked via OpenRouter before being accepted
- **O11 Only badges** — Questions only relevant to OutSystems 11 are labelled clearly

## Quick Start — Local Development

### Requirements
- Python 3.9+
- No database setup needed (SQLite is used automatically)

### Steps

```bash
# 1. Clone or download the project
git clone <repo-url>
cd outsystems-exam

# 2. Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set the required admin key
export GENERATE_API_KEY=your-secret-admin-key   # Linux / macOS
set GENERATE_API_KEY=your-secret-admin-key      # Windows

# 5. Run the app
python app.py
```

Open `http://localhost:5000` in your browser. A `users.db` SQLite file is created automatically on first run — no database setup required.

> **Note:** The `users.db` file is not committed to source control. It is a local runtime artefact; do not share it.

## Replit Deployment

On Replit, the app automatically switches from SQLite to the Replit-managed **PostgreSQL** database, which persists across all deployments. No code changes are needed.

See [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) for full Replit setup instructions.

## Project Structure

```
outsystems-exam/
├── app.py                      # Flask routes and business logic
├── db.py                       # DB adapter (auto-selects SQLite or PostgreSQL)
├── storage.py                  # Object Storage adapter for uploaded batches
├── requirements.txt            # Python dependencies
├── questions/
│   └── outsystems-odc-associate.json   # Built-in question batch
└── templates/
    ├── landing.html            # Login / register + batch selector
    ├── index.html              # Exam interface
    ├── history.html            # Attempt history list
    └── attempt_detail.html     # Per-attempt question review
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GENERATE_API_KEY` | **Yes** | Admin key for batch generation and upload endpoints |
| `DATABASE_URL` | Replit only | PostgreSQL URL — set automatically by Replit |
| `OPENROUTER_API_KEY` | Optional | Enables AI batch generation and content verification |
| `OPENROUTER_MODEL` | Optional | AI model (default: `google/gemma-4-31b-it:free`) |
| `REPLIT_OBJECT_STORAGE_BUCKET_ID` | Replit only | Auto-detected; persists uploaded batches across deploys |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Landing page (login / register / batch selector) |
| `POST` | `/login` | Authenticate user |
| `POST` | `/register` | Create account |
| `GET` | `/logout` | Clear session |
| `GET` | `/change-pin` | Change PIN form |
| `POST` | `/change-pin` | Submit PIN change |
| `GET` | `/exam` | Start exam (requires active attempt in session) |
| `GET` | `/reset` | Abandon current attempt and return to landing |
| `GET` | `/history` | Attempt history list |
| `GET` | `/history/<id>` | Detailed review of a specific attempt |
| `GET` | `/api/questions` | Return shuffled questions for current session |
| `POST` | `/api/save-answer` | Save a single answer |
| `POST` | `/api/toggle-flag` | Flag / unflag a question |
| `GET` | `/api/time-remaining` | Seconds remaining in current exam |
| `POST` | `/api/submit` | Submit exam, grade, store results |
| `POST` | `/api/generate-batch` | (Admin) AI-generate a new question batch |
| `POST` | `/api/upload-batch` | (Admin) Upload a JSON question batch |

Admin endpoints require the header `X-Admin-Key: <GENERATE_API_KEY>`.

## Adding or Modifying Questions

Questions are stored as JSON files in the `questions/` directory. Each file follows this schema:

```json
{
  "name": "Batch display name",
  "questions": [
    {
      "id": 1,
      "category": "Category Name",
      "subcategory": "Sub Name",
      "question": "Question text?",
      "options": ["A) First option", "B) Second option", "C) Third option", "D) Fourth option"],
      "correct": "B",
      "explanation": "Explanation of why B is correct.",
      "o11_only": false
    }
  ]
}
```

Drop a new JSON file into `questions/` and restart the server — it appears automatically in the batch selector.

## Troubleshooting

**Port 5000 already in use**
Change the port in `app.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, port=5001)
```

**`ModuleNotFoundError`**
Run `pip install -r requirements.txt` and ensure your virtual environment is activated.

**Lost data after restart (local)**
The `users.db` SQLite file should persist between runs. Check it was not accidentally deleted. If you need durability across machines, use a PostgreSQL instance and set `DATABASE_URL`.

**Lost data after Replit deploy**
This should not happen if PostgreSQL is configured correctly. Verify `DATABASE_URL` is set in the Replit secrets panel. See [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md).
