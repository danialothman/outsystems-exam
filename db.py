import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                pin_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                batch_key TEXT NOT NULL,
                batch_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'in_progress',
                score INTEGER,
                total INTEGER,
                percentage REAL,
                passed INTEGER,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                results_json TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()
    # Migrate existing DB — add results_json if not present
    with get_db() as conn:
        try:
            conn.execute('ALTER TABLE attempts ADD COLUMN results_json TEXT')
            conn.commit()
        except Exception:
            pass


def register_user(username, pin):
    """Register a new user. Returns (user_id, None) or (None, error_str)."""
    username = username.strip()
    if not username or len(username) < 3 or len(username) > 20:
        return None, 'Username must be 3–20 characters.'
    if not username.replace('_', '').isalnum():
        return None, 'Username may only contain letters, numbers, and underscores.'
    if not pin or not pin.isdigit() or len(pin) < 4 or len(pin) > 8:
        return None, 'PIN must be 4–8 digits.'
    pin_hash = generate_password_hash(pin)
    try:
        with get_db() as conn:
            cur = conn.execute(
                'INSERT INTO users (username, pin_hash) VALUES (?, ?)',
                (username, pin_hash)
            )
            conn.commit()
            return cur.lastrowid, None
    except sqlite3.IntegrityError:
        return None, 'Username already taken. Please choose another.'


def login_user(username, pin):
    """Validate credentials. Returns (user_id, None) or (None, error_str)."""
    username = username.strip()
    with get_db() as conn:
        row = conn.execute(
            'SELECT id, pin_hash FROM users WHERE username = ?', (username,)
        ).fetchone()
    if not row:
        return None, 'Username not found.'
    if not check_password_hash(row['pin_hash'], pin):
        return None, 'Incorrect PIN.'
    return row['id'], None


def create_attempt(user_id, batch_key, batch_name):
    """Create a new in-progress attempt. Returns attempt_id."""
    with get_db() as conn:
        cur = conn.execute(
            '''INSERT INTO attempts (user_id, batch_key, batch_name, status, started_at)
               VALUES (?, ?, ?, 'in_progress', ?)''',
            (user_id, batch_key, batch_name, datetime.now().isoformat())
        )
        conn.commit()
        return cur.lastrowid


def complete_attempt(attempt_id, score, total, percentage, passed, results_json=None):
    """Mark an attempt as completed with full results."""
    with get_db() as conn:
        conn.execute(
            '''UPDATE attempts
               SET status='completed', score=?, total=?, percentage=?, passed=?,
                   finished_at=?, results_json=?
               WHERE id=?''',
            (score, total, round(percentage, 1), 1 if passed else 0,
             datetime.now().isoformat(), results_json, attempt_id)
        )
        conn.commit()


def abandon_attempt(attempt_id, score=None, total=None, percentage=None):
    """Mark an in-progress attempt as abandoned. Safe to call even if already completed."""
    with get_db() as conn:
        conn.execute(
            '''UPDATE attempts
               SET status='abandoned', score=?, total=?, percentage=?, finished_at=?
               WHERE id=? AND status='in_progress' ''',
            (score, total,
             round(percentage, 1) if percentage is not None else None,
             datetime.now().isoformat(), attempt_id)
        )
        conn.commit()


def get_user_attempts(user_id):
    """Return all attempts for a user, newest first."""
    with get_db() as conn:
        rows = conn.execute(
            '''SELECT id, batch_key, batch_name, status, score, total, percentage,
                      passed, started_at, finished_at
               FROM attempts WHERE user_id = ? ORDER BY started_at DESC''',
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_attempt_detail(attempt_id, user_id):
    """Return a single attempt (with results_json) belonging to user_id, or None."""
    with get_db() as conn:
        row = conn.execute(
            '''SELECT id, batch_key, batch_name, status, score, total, percentage,
                      passed, started_at, finished_at, results_json
               FROM attempts WHERE id = ? AND user_id = ?''',
            (attempt_id, user_id)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id):
    """Return user row by id."""
    with get_db() as conn:
        row = conn.execute(
            'SELECT id, username, created_at FROM users WHERE id = ?', (user_id,)
        ).fetchone()
        return dict(row) if row else None


def change_pin(user_id, current_pin, new_pin):
    """Change a user's PIN. Returns (True, None) or (False, error_str)."""
    if not new_pin or not new_pin.isdigit() or len(new_pin) < 4 or len(new_pin) > 8:
        return False, 'New PIN must be 4–8 digits.'
    with get_db() as conn:
        row = conn.execute(
            'SELECT pin_hash FROM users WHERE id = ?', (user_id,)
        ).fetchone()
    if not row:
        return False, 'User not found.'
    if not check_password_hash(row['pin_hash'], current_pin):
        return False, 'Current PIN is incorrect.'
    new_hash = generate_password_hash(new_pin)
    with get_db() as conn:
        conn.execute('UPDATE users SET pin_hash = ? WHERE id = ?', (new_hash, user_id))
        conn.commit()
    return True, None
