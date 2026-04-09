# OutSystems Exam Simulator

A Flask web application for practising OutSystems certification exams with user accounts, attempt history, and AI-assisted question generation.

## Architecture

| File | Purpose |
|---|---|
| `app.py` | Flask app — all routes and business logic |
| `db.py` | Unified database adapter (PostgreSQL or SQLite — see below) |
| `storage.py` | Object Storage adapter for question-batch persistence |
| `templates/landing.html` | Login / register page + batch selector |
| `templates/index.html` | Live exam interface |
| `templates/history.html` | Attempt history list |
| `templates/attempt_detail.html` | Per-attempt question review |
| `questions/` | Built-in question batches (JSON files) |

## Database — dual-backend design

`db.py` automatically chooses its backend at startup:

| Environment | Backend | How |
|---|---|---|
| **Replit (deployed)** | PostgreSQL | `DATABASE_URL` env var is set automatically by Replit |
| **Local development** | SQLite (`users.db`) | `DATABASE_URL` is absent; file is auto-created |

No code changes are needed to switch between environments — `db.py` inspects `DATABASE_URL` and selects the correct driver, DDL, and query placeholder style (`%s` vs `?`) at import time.

### Why this matters for deployment
SQLite data lives inside the project directory. Replit rebuilds that directory from source on every deploy, so any SQLite data is lost. PostgreSQL is a separate, persistent service managed by Replit — data survives all deployments. Always use the Replit-provisioned PostgreSQL for any shared or production environment.

## Key Features

- **User accounts** — Username + numeric PIN (4–8 digits); no admin required
- **Account expiry** — Accounts expire 30 days after registration; users can change their PIN
- **Attempt tracking** — Every exam attempt recorded as `in_progress`, `completed`, or `abandoned`
- **Attempt detail view** — Full question-by-question review with correct answers and explanations
- **Answer shuffling** — Options are shuffled per question using a per-session seed for consistency
- **Question batches** — Built-in, AI-generated, or user-uploaded JSON batches
- **AI content verification** — Uploaded batches verified via Claude (OpenRouter) before acceptance
- **O11 Only badges** — Questions flagged as OutSystems 11-specific are shown in amber

## User Flow

1. `GET /` → login or register form
2. After auth, user sees batch selector (built-in + any uploaded batches)
3. Pick a batch → Start Exam → attempt created in DB
4. During exam, answers saved per question; option order shuffled but consistent
5. On submit → attempt marked `completed` with full `results_json` stored
6. Navigating away (`/reset`) → attempt marked `abandoned`
7. `GET /history` → list of all attempts with "View Details" link
8. `GET /history/<id>` → question-by-question review for that attempt

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Replit only | PostgreSQL connection string (auto-set by Replit) |
| `GENERATE_API_KEY` | Yes | Admin key for `/api/generate-batch` and `/api/upload-batch` |
| `OPENROUTER_API_KEY` | Optional | Enables AI generation and content verification |
| `OPENROUTER_MODEL` | Optional | Model for generation (default: `google/gemma-4-31b-it:free`) |
| `REPLIT_OBJECT_STORAGE_BUCKET_ID` | Replit only | Auto-detected; used to persist uploaded batches |

## Security

- PINs hashed with Werkzeug `generate_password_hash` (pbkdf2:sha256)
- Admin endpoints require `X-Admin-Key: <GENERATE_API_KEY>` header
- Session stores only `user_id` and `username`
- `login_required` decorator guards `/exam`, `/history`, and `/history/<id>`

## Rate Limits

- Upload: 5 per IP per hour, 20 global per hour
- Generation: 1 per IP per 24 hours

## Question Batch Format

```json
{
  "name": "Batch display name",
  "questions": [
    {
      "id": 1,
      "category": "Category Name",
      "subcategory": "Sub Name",
      "question": "Question text?",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct": "B",
      "explanation": "Why B is correct.",
      "o11_only": false
    }
  ]
}
```
