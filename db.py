import os
import psycopg2
import psycopg2.extras
from psycopg2 import errors as pg_errors
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL')


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    pin_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS attempts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    batch_key TEXT NOT NULL,
                    batch_name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'in_progress',
                    score INTEGER,
                    total INTEGER,
                    percentage REAL,
                    passed INTEGER,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP,
                    results_json TEXT
                )
            ''')
        conn.commit()


def _fmt_ts(val):
    """Format a datetime or string timestamp to ISO string, or return None."""
    if val is None:
        return None
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    return str(val)


def _normalise(d):
    """Convert any datetime values in a dict to ISO strings."""
    for k in ('started_at', 'finished_at', 'created_at'):
        if k in d:
            d[k] = _fmt_ts(d[k])
    return d


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
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO users (username, pin_hash) VALUES (%s, %s) RETURNING id',
                    (username, pin_hash)
                )
                user_id = cur.fetchone()[0]
            conn.commit()
            return user_id, None
    except Exception as e:
        if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
            return None, 'Username already taken. Please choose another.'
        return None, 'Registration failed. Please try again.'


def login_user(username, pin):
    """Validate credentials. Returns (user_id, None) or (None, error_str)."""
    username = username.strip().lower()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, pin_hash FROM users WHERE username = %s', (username,)
            )
            row = cur.fetchone()
    if not row:
        return None, 'Username not found.'
    if not check_password_hash(row[1], pin):
        return None, 'Incorrect PIN.'
    return row[0], None


def create_attempt(user_id, batch_key, batch_name):
    """Create a new in-progress attempt. Returns attempt_id."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO attempts (user_id, batch_key, batch_name, status, started_at)
                   VALUES (%s, %s, %s, 'in_progress', %s) RETURNING id''',
                (user_id, batch_key, batch_name, datetime.now().isoformat())
            )
            attempt_id = cur.fetchone()[0]
        conn.commit()
        return attempt_id


def complete_attempt(attempt_id, score, total, percentage, passed, results_json=None):
    """Mark an attempt as completed with full results."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''UPDATE attempts
                   SET status='completed', score=%s, total=%s, percentage=%s, passed=%s,
                       finished_at=%s, results_json=%s
                   WHERE id=%s''',
                (score, total, round(percentage, 1), 1 if passed else 0,
                 datetime.now().isoformat(), results_json, attempt_id)
            )
        conn.commit()


def abandon_attempt(attempt_id, score=None, total=None, percentage=None):
    """Mark an in-progress attempt as abandoned. Safe to call even if already completed."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''UPDATE attempts
                   SET status='abandoned', score=%s, total=%s, percentage=%s, finished_at=%s
                   WHERE id=%s AND status='in_progress' ''',
                (score, total,
                 round(percentage, 1) if percentage is not None else None,
                 datetime.now().isoformat(), attempt_id)
            )
        conn.commit()


def get_user_attempts(user_id):
    """Return all attempts for a user, newest first."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, batch_key, batch_name, status, score, total, percentage,
                          passed, started_at, finished_at,
                          CASE WHEN results_json IS NOT NULL THEN 1 ELSE 0 END AS has_detail
                   FROM attempts WHERE user_id = %s ORDER BY started_at DESC''',
                (user_id,)
            )
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
    return [_normalise(dict(zip(cols, r))) for r in rows]


def get_attempt_detail(attempt_id, user_id):
    """Return a single attempt (with results_json) belonging to user_id, or None."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, batch_key, batch_name, status, score, total, percentage,
                          passed, started_at, finished_at, results_json
                   FROM attempts WHERE id = %s AND user_id = %s''',
                (attempt_id, user_id)
            )
            row = cur.fetchone()
            cols = [desc[0] for desc in cur.description] if row else []
    return _normalise(dict(zip(cols, row))) if row else None


def get_user_by_id(user_id):
    """Return user row by id."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, username, created_at FROM users WHERE id = %s', (user_id,)
            )
            row = cur.fetchone()
            cols = [desc[0] for desc in cur.description] if row else []
    return _normalise(dict(zip(cols, row))) if row else None


def change_pin(user_id, current_pin, new_pin):
    """Change a user's PIN. Returns (True, None) or (False, error_str)."""
    if not new_pin or not new_pin.isdigit() or len(new_pin) < 4 or len(new_pin) > 8:
        return False, 'New PIN must be 4–8 digits.'
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT pin_hash FROM users WHERE id = %s', (user_id,))
            row = cur.fetchone()
    if not row:
        return False, 'User not found.'
    if not check_password_hash(row[0], current_pin):
        return False, 'Current PIN is incorrect.'
    new_hash = generate_password_hash(new_pin)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE users SET pin_hash = %s WHERE id = %s', (new_hash, user_id))
        conn.commit()
    return True, None
