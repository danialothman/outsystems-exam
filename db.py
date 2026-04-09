"""
Database adapter — auto-selects backend:
  - PostgreSQL  when DATABASE_URL is set  (Replit deployment)
  - SQLite      otherwise                 (local development)
"""
import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_URL = os.environ.get('DATABASE_URL')
_USE_PG = bool(DATABASE_URL)

DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')

# Query placeholder: %s for PostgreSQL, ? for SQLite
PH = '%s' if _USE_PG else '?'

if _USE_PG:
    import psycopg2


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _conn():
    """Open a database connection for the active backend."""
    if _USE_PG:
        return psycopg2.connect(DATABASE_URL)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(cur):
    """Fetch all rows as a list of plain dicts."""
    if _USE_PG:
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    return [dict(r) for r in cur.fetchall()]


def _row(cur):
    """Fetch one row as a plain dict, or None."""
    if _USE_PG:
        r = cur.fetchone()
        if r is None:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, r))
    r = cur.fetchone()
    return dict(r) if r else None


def _insert_id(cur, sql, params):
    """Run an INSERT and return the new row id."""
    if _USE_PG:
        cur.execute(sql + ' RETURNING id', params)
        return cur.fetchone()[0]
    cur.execute(sql, params)
    return cur.lastrowid


def _fmt_ts(val):
    """Normalise a timestamp to an ISO string (handles datetime objects and strings)."""
    if val is None:
        return None
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    return str(val)


def _normalise(d):
    """Convert datetime fields to ISO strings so templates can do string slicing."""
    for k in ('started_at', 'finished_at', 'created_at'):
        if k in d:
            d[k] = _fmt_ts(d[k])
    return d


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def init_db():
    """Create tables if they don't already exist."""
    with _conn() as conn:
        cur = conn.cursor()
        if _USE_PG:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id          SERIAL PRIMARY KEY,
                    username    TEXT UNIQUE NOT NULL,
                    pin_hash    TEXT NOT NULL,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS attempts (
                    id           SERIAL PRIMARY KEY,
                    user_id      INTEGER NOT NULL REFERENCES users(id),
                    batch_key    TEXT NOT NULL,
                    batch_name   TEXT NOT NULL,
                    status       TEXT NOT NULL DEFAULT 'in_progress',
                    score        INTEGER,
                    total        INTEGER,
                    percentage   REAL,
                    passed       INTEGER,
                    started_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at  TIMESTAMP,
                    results_json TEXT
                )
            ''')
        else:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    username    TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    pin_hash    TEXT NOT NULL,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS attempts (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id      INTEGER NOT NULL,
                    batch_key    TEXT NOT NULL,
                    batch_name   TEXT NOT NULL,
                    status       TEXT NOT NULL DEFAULT 'in_progress',
                    score        INTEGER,
                    total        INTEGER,
                    percentage   REAL,
                    passed       INTEGER,
                    started_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at  TIMESTAMP,
                    results_json TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            # Migrate older SQLite DBs that predate results_json
            try:
                cur.execute('ALTER TABLE attempts ADD COLUMN results_json TEXT')
            except Exception:
                pass
        conn.commit()


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

def register_user(username, pin):
    """Register a new user. Returns (user_id, None) or (None, error_str)."""
    username = username.strip().lower()
    if not username or len(username) < 3 or len(username) > 20:
        return None, 'Username must be 3–20 characters.'
    if not username.replace('_', '').isalnum():
        return None, 'Username may only contain letters, numbers, and underscores.'
    if not pin or not pin.isdigit() or len(pin) < 4 or len(pin) > 8:
        return None, 'PIN must be 4–8 digits.'
    pin_hash = generate_password_hash(pin)
    try:
        with _conn() as conn:
            cur = conn.cursor()
            user_id = _insert_id(
                cur,
                f'INSERT INTO users (username, pin_hash) VALUES ({PH}, {PH})',
                (username, pin_hash)
            )
            conn.commit()
            return user_id, None
    except Exception as e:
        msg = str(e).lower()
        if 'unique' in msg or 'duplicate' in msg:
            return None, 'Username already taken. Please choose another.'
        return None, 'Registration failed. Please try again.'


def login_user(username, pin):
    """Validate credentials. Returns (user_id, None) or (None, error_str)."""
    username = username.strip().lower()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(f'SELECT id, pin_hash FROM users WHERE username = {PH}', (username,))
        row = cur.fetchone()
    if not row:
        return None, 'Username not found.'
    pin_hash = row[1] if _USE_PG else row['pin_hash']
    user_id  = row[0] if _USE_PG else row['id']
    if not check_password_hash(pin_hash, pin):
        return None, 'Incorrect PIN.'
    return user_id, None


def get_user_by_id(user_id):
    """Return user row by id."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f'SELECT id, username, created_at FROM users WHERE id = {PH}',
            (user_id,)
        )
        d = _row(cur)
    return _normalise(d) if d else None


def change_pin(user_id, current_pin, new_pin):
    """Change a user's PIN. Returns (True, None) or (False, error_str)."""
    if not new_pin or not new_pin.isdigit() or len(new_pin) < 4 or len(new_pin) > 8:
        return False, 'New PIN must be 4–8 digits.'
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(f'SELECT pin_hash FROM users WHERE id = {PH}', (user_id,))
        row = cur.fetchone()
    if not row:
        return False, 'User not found.'
    stored_hash = row[0] if _USE_PG else row['pin_hash']
    if not check_password_hash(stored_hash, current_pin):
        return False, 'Current PIN is incorrect.'
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f'UPDATE users SET pin_hash = {PH} WHERE id = {PH}',
            (generate_password_hash(new_pin), user_id)
        )
        conn.commit()
    return True, None


# ---------------------------------------------------------------------------
# Attempt tracking
# ---------------------------------------------------------------------------

def create_attempt(user_id, batch_key, batch_name):
    """Create a new in-progress attempt. Returns attempt_id."""
    with _conn() as conn:
        cur = conn.cursor()
        attempt_id = _insert_id(
            cur,
            f'''INSERT INTO attempts (user_id, batch_key, batch_name, status, started_at)
                VALUES ({PH}, {PH}, {PH}, 'in_progress', {PH})''',
            (user_id, batch_key, batch_name, datetime.now().isoformat())
        )
        conn.commit()
    return attempt_id


def complete_attempt(attempt_id, score, total, percentage, passed, results_json=None):
    """Mark an attempt as completed with full results."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f'''UPDATE attempts
               SET status='completed', score={PH}, total={PH}, percentage={PH},
                   passed={PH}, finished_at={PH}, results_json={PH}
               WHERE id={PH}''',
            (score, total, round(percentage, 1), 1 if passed else 0,
             datetime.now().isoformat(), results_json, attempt_id)
        )
        conn.commit()


def abandon_attempt(attempt_id, score=None, total=None, percentage=None):
    """Mark an in-progress attempt as abandoned. Safe to call after completion."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f'''UPDATE attempts
               SET status='abandoned', score={PH}, total={PH}, percentage={PH},
                   finished_at={PH}
               WHERE id={PH} AND status='in_progress' ''',
            (score, total,
             round(percentage, 1) if percentage is not None else None,
             datetime.now().isoformat(), attempt_id)
        )
        conn.commit()


def get_user_attempts(user_id):
    """Return all attempts for a user, newest first."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f'''SELECT id, batch_key, batch_name, status, score, total, percentage,
                       passed, started_at, finished_at,
                       CASE WHEN results_json IS NOT NULL THEN 1 ELSE 0 END AS has_detail
               FROM attempts WHERE user_id = {PH} ORDER BY started_at DESC''',
            (user_id,)
        )
        rows = _rows(cur)
    return [_normalise(r) for r in rows]


def get_attempt_detail(attempt_id, user_id):
    """Return a single attempt (with results_json) belonging to user_id, or None."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f'''SELECT id, batch_key, batch_name, status, score, total, percentage,
                       passed, started_at, finished_at, results_json
               FROM attempts WHERE id = {PH} AND user_id = {PH}''',
            (attempt_id, user_id)
        )
        d = _row(cur)
    return _normalise(d) if d else None
