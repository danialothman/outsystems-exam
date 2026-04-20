# Feature Summary — OutSystems Exam Simulator

Current state of the application as of the PostgreSQL migration.

---

## User Accounts

- [x] Register with username (3–20 chars, alphanumeric + underscore) and numeric PIN (4–8 digits)
- [x] Usernames stored lowercase; case-insensitive login
- [x] PINs hashed with Werkzeug pbkdf2:sha256 — never stored in plaintext
- [x] Change PIN with current-PIN verification
- [x] Accounts and user data are retained indefinitely (no expiry, no automatic deletion)
- [x] `login_required` decorator protects exam, history, and detail routes

## Database — dual-backend

- [x] **SQLite** used automatically for local development (no setup needed; `users.db` auto-created)
- [x] **PostgreSQL** used automatically on Replit when `DATABASE_URL` is present
- [x] Same `db.py` module handles both — no code changes needed between environments
- [x] Automatic schema creation (`init_db()`) on first run for both backends
- [x] SQLite migration guard for older `.db` files missing the `results_json` column

## Exam Engine

- [x] Question batches loaded from `questions/` directory (JSON files)
- [x] Additional batches persisted in Replit Object Storage (survive deploys)
- [x] Attempt created in DB when exam starts (`status = in_progress`)
- [x] Answer shuffling: option order randomised per question with a per-session seed, consistent across save and submit
- [x] Answers saved per question via `/api/save-answer`
- [x] Question flagging (flag / unflag) persisted in session
- [x] 120-minute countdown timer with server-side tracking; auto-submit on expiry
- [x] Timer colour: normal (white) → warning (yellow, <10 min) → critical (red pulsing, <5 min)
- [x] Keyboard navigation: arrow keys move between questions

## Attempt Lifecycle

- [x] `in_progress` — attempt started but not yet submitted
- [x] `completed` — exam submitted; score, percentage, pass/fail, and full `results_json` stored
- [x] `abandoned` — user navigated away via `/reset`; partial score recorded if available
- [x] Attempt history list at `/history` — all attempts newest first
- [x] "View Details →" link shown only when `results_json` is present

## Attempt Detail View

- [x] Score summary card with pass/fail badge
- [x] Category breakdown with percentage bars
- [x] Filter question cards: All / Correct / Incorrect
- [x] Each card shows: question text, all options (with correct and user-selected highlighted), explanation
- [x] Notice shown for old attempts without stored results

## AI Features (optional)

- [x] `/api/generate-batch` — generate a new question batch via OpenRouter (requires `OPENROUTER_API_KEY`)
- [x] `/api/upload-batch` — upload a JSON batch; content verified by AI before acceptance
- [x] O11 Only badge: questions with `"o11_only": true` shown with an amber label
- [x] HTML entity decoding in `escapeHtml()` prevents double-encoding artifacts from AI-generated text

## Security

- [x] Admin endpoints (`/api/generate-batch`, `/api/upload-batch`) require `X-Admin-Key` header
- [x] Rate limiting: upload 5/IP/hour, 20 global/hour; generation 1/IP/24h
- [x] Correct answers never sent to the client
- [x] Server-side grading only

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | — | Landing / login / batch selector |
| `POST` | `/login` | — | Authenticate |
| `POST` | `/register` | — | Create account |
| `GET` | `/logout` | — | Clear session |
| `GET/POST` | `/change-pin` | User | Change PIN |
| `GET` | `/exam` | User | Exam interface |
| `GET` | `/reset` | User | Abandon attempt + return to landing |
| `GET` | `/history` | User | Attempt history list |
| `GET` | `/history/<id>` | User | Attempt detail view |
| `GET` | `/api/questions` | User | Shuffled questions for session |
| `POST` | `/api/save-answer` | User | Save one answer |
| `POST` | `/api/toggle-flag` | User | Flag / unflag question |
| `GET` | `/api/time-remaining` | User | Seconds remaining |
| `POST` | `/api/submit` | User | Submit + grade |
| `POST` | `/api/generate-batch` | Admin | AI batch generation |
| `POST` | `/api/upload-batch` | Admin | JSON batch upload |

## Known Limitations

- Flask sessions are in-memory: exam progress is lost if the server restarts mid-exam
- No multi-worker session sharing (single-process only unless Redis sessions are added)
- No admin UI — batch management is via API calls with the admin key
- Mobile layout is functional but not optimised for small screens
