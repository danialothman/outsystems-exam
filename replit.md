# OutSystems Exam Simulator

A Flask web application for practicing OutSystems certification exams.

## Architecture

- **`app.py`** — Flask app, all routes and business logic
- **`db.py`** — SQLite user management and attempt tracking
- **`storage.py`** — Object Storage adapter for batch persistence
- **`templates/landing.html`** — Landing page with login/register + batch selection
- **`templates/index.html`** — Exam interface
- **`templates/history.html`** — User attempt history page
- **`questions/`** — Built-in question batches (JSON)
- **`users.db`** — SQLite database (auto-created on first run)

## Key Features

- **User accounts** — Username + numeric PIN; no admin required
- **Attempt tracking** — Every exam attempt is saved (completed, abandoned, in-progress)
- **Exam history** — Users can review all past attempts with scores and pass/fail status
- **Question review** — Full question-by-question review with correct answers and explanations on results page
- **Question batches** — Built-in, AI-generated, or user-uploaded JSON batches
- **AI content verification** — Uploaded batches verified via Claude (OpenRouter) before acceptance
- **O11 Only badges** — Questions flagged as OutSystems 11-specific are badged in amber
- **Keyboard navigation** — Arrow keys to navigate questions during exam
- **Loading spinners** — Spinner on Start Exam button and exam loading state

## User Flow

1. User visits `/` → sees login/register form
2. After login/register, user sees batch selector
3. User picks a batch, clicks Start Exam → attempt created in DB
4. User completes exam or navigates away:
   - Submit → attempt marked `completed` with score/pass/fail
   - Navigate away (`/reset`) → attempt marked `abandoned`
5. User can view full history at `/history`

## Security

- PIN hashed with werkzeug `generate_password_hash`
- Admin endpoints (`/api/generate-batch`, `/api/upload-batch`) require `X-Admin-Key` header
- Session stores `user_id` + `username`
- `login_required` decorator guards `/exam` and `/history`

## Environment Variables

- `GENERATE_API_KEY` — Admin key for generate/upload endpoints
- `OPENROUTER_API_KEY` — For AI content verification and generation
- `OPENROUTER_MODEL` — Model for generation (default: `google/gemma-4-31b-it:free`)
- `REPLIT_OBJECT_STORAGE_BUCKET_ID` — Auto-detected on Replit

## Rate Limits

- Upload: 5 per IP per hour, 20 global per hour
- Generation: 1 per IP per 24 hours (paid models)
