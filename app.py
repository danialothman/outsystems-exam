from flask import Flask, render_template, request, jsonify, session, redirect
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from storage import load_all_batches, save_batch
import urllib.request
import urllib.error
import random
import json
import os
import re
import html as html_mod
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')

app = Flask(__name__)
app.secret_key = 'outsystems-exam-simulator-2024'

MAX_UPLOAD_SIZE = 2 * 1024 * 1024  # 2MB

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'google/gemma-4-31b-it:free')
GENERATE_API_KEY = os.environ.get('GENERATE_API_KEY', '')

def _check_admin_key():
    """Return (allowed, error_response) based on X-Admin-Key header."""
    if not GENERATE_API_KEY:
        return False, (jsonify({'error': 'GENERATE_API_KEY is not configured on the server.'}), 503)
    provided = request.headers.get('X-Admin-Key', '')
    if not provided:
        return False, (jsonify({'error': 'Missing X-Admin-Key header.'}), 401)
    import hmac as _hmac
    if not _hmac.compare_digest(provided, GENERATE_API_KEY):
        return False, (jsonify({'error': 'Invalid admin key.'}), 403)
    return True, None

def sanitize_str(value):
    """Escape HTML entities to prevent XSS."""
    if not isinstance(value, str):
        return value
    return html_mod.escape(value)


def verify_questions_with_ai(questions):
    """
    Sample up to 15 questions and ask the AI to strictly verify they are
    factually accurate OutSystems exam questions.
    Returns (ok: bool, reason: str).
    Fails closed — any error blocks the upload.
    """
    if not OPENROUTER_API_KEY:
        return False, 'Content verification unavailable: OpenRouter API key not configured.'

    sample = random.sample(questions, min(15, len(questions)))
    sample_text = ''
    for i, q in enumerate(sample, 1):
        sample_text += f"Q{i}: {q['question']}\n"
        for opt in q['options']:
            sample_text += f"  {opt}\n"
        sample_text += f"  Correct: {q['correct']}\n"
        if q.get('explanation'):
            sample_text += f"  Explanation: {q['explanation']}\n"
        sample_text += '\n'

    prompt = (
        "You are a strict OutSystems platform expert and exam content reviewer. "
        "Your job is to reject any question batch that contains inaccurate, fabricated, "
        "misleading, or non-OutSystems content.\n\n"
        "Review the following exam questions carefully. Reject the batch (ok=false) if ANY of the following apply:\n"
        "- Any question contains invented or incorrect limits, thresholds, or numeric values\n"
        "- Any question references technology names, features, or concepts that do not exist in OutSystems\n"
        "- Any question contains false statements about OutSystems ODC or Traditional OutSystems behaviour\n"
        "- Any explanation contradicts known OutSystems documentation\n"
        "- Any question is generic/non-OutSystems content disguised as an OutSystems question\n"
        "- Any question has a correct answer that is actually wrong\n"
        "- The content does not appear to be genuinely about OutSystems certifications\n\n"
        "When in doubt, set ok=false. Only approve if you are confident every sampled question is accurate.\n\n"
        f"{sample_text}\n"
        "Reply with ONLY a JSON object in this exact format, no other text:\n"
        '{"ok": true, "reason": ""}\n'
        "If rejecting, set ok=false and provide a concise reason citing the specific problem found."
    )

    payload = json.dumps({
        "model": "anthropic/claude-3-5-haiku",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 300,
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/chat/completions',
        data=payload,
        headers={
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:5000',
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        content = result['choices'][0]['message']['content'].strip()
        fence_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', content)
        if fence_match:
            content = fence_match.group(1)
        verdict = json.loads(content)
        return bool(verdict.get('ok', False)), str(verdict.get('reason', ''))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return False, 'Content check rate limit reached. Please try again later.'
        return False, f'Content verification failed (HTTP {e.code}). Upload rejected.'
    except Exception as e:
        logging.warning(f'Content verification error: {e}')
        return False, 'Content verification could not be completed. Upload rejected.'


def check_topic_diversity(topic, existing_batches):
    """
    Ask AI whether the requested topic is too similar to existing batches.
    Returns (ok: bool, reason: str).
    """
    if not OPENROUTER_API_KEY or not existing_batches:
        return True, ''

    batch_list = '\n'.join(f'- {b["name"]}' for b in existing_batches)

    prompt = (
        "You are evaluating whether a new exam question batch would be too similar to existing ones.\n\n"
        f"Requested topic: {topic}\n\n"
        f"Existing batches:\n{batch_list}\n\n"
        "Reply with ONLY a JSON object in this exact format:\n"
        '{"ok": true, "reason": ""}\n'
        "Set ok=false and provide a short reason if the new topic would produce questions that "
        "significantly overlap with an existing batch (same certification, same core subject area). "
        "Set ok=true if the new topic is sufficiently different or adds meaningful new coverage."
    )

    payload = json.dumps({
        "model": "anthropic/claude-3-5-haiku",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 150,
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/chat/completions',
        data=payload,
        headers={
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:5000',
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        content = result['choices'][0]['message']['content'].strip()
        fence_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', content)
        if fence_match:
            content = fence_match.group(1)
        verdict = json.loads(content)
        return bool(verdict.get('ok', True)), str(verdict.get('reason', ''))
    except Exception:
        return True, ''


BATCHES = load_all_batches()

def reload_batches():
    """Refresh BATCHES from storage in-place so deletions/additions are reflected immediately."""
    fresh = load_all_batches()
    BATCHES.clear()
    BATCHES.update(fresh)

UPLOAD_RATE_PER_IP = 5      # max uploads per IP per hour
UPLOAD_RATE_GLOBAL = 20     # max uploads across all IPs per hour
_upload_log = []            # list of (timestamp, ip) tuples

PAID_GEN_LIMIT_PER_IP = 1   # max paid generations per IP per 24 hours
_paid_gen_log = []          # list of (timestamp, ip) tuples

def _check_paid_gen_rate(ip):
    """Returns (allowed: bool, reason: str). 1 paid generation per IP per 24 hours."""
    from datetime import timezone
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    global _paid_gen_log
    _paid_gen_log = [(t, i) for t, i in _paid_gen_log if t > cutoff]
    ip_count = sum(1 for _, i in _paid_gen_log if i == ip)
    if ip_count >= PAID_GEN_LIMIT_PER_IP:
        return False, 'Paid generation limit reached (1 per IP per 24 hours). Use the free model or try again tomorrow.'
    _paid_gen_log.append((now, ip))
    return True, ''

def _check_upload_rate(ip):
    """Returns (allowed: bool, reason: str). Prunes entries older than 1 hour."""
    from datetime import timezone
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=1)
    global _upload_log
    _upload_log = [(t, i) for t, i in _upload_log if t > cutoff]
    global_count = len(_upload_log)
    ip_count = sum(1 for _, i in _upload_log if i == ip)
    if global_count >= UPLOAD_RATE_GLOBAL:
        return False, f'Global upload limit reached ({UPLOAD_RATE_GLOBAL}/hour). Try again later.'
    if ip_count >= UPLOAD_RATE_PER_IP:
        return False, f'Upload limit reached ({UPLOAD_RATE_PER_IP}/hour). Try again later.'
    _upload_log.append((now, ip))
    return True, ''


def get_session_questions():
    """Get ordered question objects from session's selected batch."""
    batch_key = session.get('batch_key')
    if not batch_key or batch_key not in BATCHES:
        return []
    questions_by_id = {q['id']: q for q in BATCHES[batch_key]['questions']}
    order = session.get('question_order', [])
    return [questions_by_id[qid] for qid in order if qid in questions_by_id]

@app.route('/')
def landing():
    """Landing page - prompt user to start exam"""
    session['ui_access'] = True
    return render_template('landing.html')

@app.route('/api/batches')
def list_batches():
    """Return available question batches."""
    reload_batches()
    from storage import QUESTIONS_DIR
    import glob as glob_mod
    local_files = {os.path.basename(f) for f in glob_mod.glob(os.path.join(QUESTIONS_DIR, '*.json'))}

    result = []
    for key, batch in BATCHES.items():
        if key in local_files:
            source = 'Built-in'
        elif key.startswith('generated_'):
            source = 'AI Generated'
        else:
            source = 'Uploaded'
        result.append({
            'key': key,
            'name': batch['name'],
            'count': batch['count'],
            'time_limit': batch['time_limit'],
            'passing_score': batch['passing_score'],
            'source': source,
        })
    return jsonify(result)

GENERATE_COOLDOWN = 120  # seconds between generations

ALLOWED_TOPICS = {
    'odc-associate': 'OutSystems ODC Associate Developer certification',
    'architecture': 'OutSystems Architecture Specialist certification',
    'web-developer': 'OutSystems Web Developer Specialist certification',
    'security': 'OutSystems Security Specialist certification',
    'mobile-developer': 'OutSystems Mobile Developer Specialist certification',
    'agentic-ai': 'OutSystems Agentic AI certification',
}

OUTSYSTEMS_KEYWORDS = [
    'outsystems', 'odc', 'entity', 'aggregate', 'screen', 'block', 'module',
    'action', 'widget', 'attribute', 'forge', 'service studio', 'integration',
    'reactive', 'traditional web', 'client action', 'server action', 'rest api',
    'timer', 'role', 'scaffold', 'lifecycle', 'fetch', 'input parameter',
    'output parameter', 'local variable', 'site property', 'static entity',
]

@app.route('/api/generate-batch', methods=['POST'])
def generate_batch():
    """Generate a question batch using OpenRouter API."""
    allowed, err = _check_admin_key()
    if not allowed:
        return err

    if not OPENROUTER_API_KEY:
        return jsonify({'error': 'OpenRouter API key not configured. Set OPENROUTER_API_KEY environment variable.'}), 400

    last_gen = session.get('last_generate')
    if last_gen:
        elapsed = (datetime.now() - datetime.fromisoformat(last_gen)).total_seconds()
        remaining = int(GENERATE_COOLDOWN - elapsed)
        if remaining > 0:
            return jsonify({'error': f'Please wait {remaining} seconds before generating again.', 'cooldown': remaining}), 429

    MODEL_FREE = 'google/gemma-4-31b-it:free'
    ALLOWED_MODELS = {MODEL_FREE, 'google/gemma-4-31b-it', 'anthropic/claude-3-5-haiku'}
    PAID_MODELS = {'google/gemma-4-31b-it', 'anthropic/claude-3-5-haiku'}

    data = request.get_json()
    topic_key = str(data.get('topic_key', '')).strip()
    if topic_key not in ALLOWED_TOPICS:
        return jsonify({'error': 'Invalid topic. Please select a preset topic.'}), 400
    topic = ALLOWED_TOPICS[topic_key]

    model = data.get('model', MODEL_FREE)
    if model not in ALLOWED_MODELS:
        model = MODEL_FREE

    if model in PAID_MODELS:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
        allowed, rate_reason = _check_paid_gen_rate(ip)
        if not allowed:
            return jsonify({'error': rate_reason}), 429

    # Diversity check — reject if topic overlaps too much with existing batches
    existing = [{'name': b['name']} for b in BATCHES.values()]
    diverse, diversity_reason = check_topic_diversity(topic, existing)
    if not diverse:
        return jsonify({'error': f'Topic too similar to an existing batch: {diversity_reason}'}), 409

    schema_example = json.dumps({
        "name": "Your Batch Name",
        "time_limit": 7200,
        "passing_score": 70,
        "questions": [{
            "id": 1,
            "category": "Topic Area",
            "subcategory": "Subtopic",
            "question": "Your question text?",
            "options": ["A) First option", "B) Second option", "C) Third option", "D) Fourth option"],
            "correct": "A",
            "explanation": "Why A is correct."
        }]
    }, indent=2)

    prompt = (
        f"Generate a practice exam as a JSON file with exactly this structure:\n\n"
        f"{schema_example}\n\n"
        f"Rules:\n"
        f"- Generate 50 multiple-choice questions on {topic}\n"
        f"- Each question must have exactly 4 options labeled A), B), C), D)\n"
        f'- "correct" must be one of: "A", "B", "C", "D"\n'
        f'- "id" must be a unique positive integer starting from 1\n'
        f'- "time_limit" is in seconds (7200 = 2 hours)\n'
        f'- "passing_score" is a percentage (70 = 70%)\n'
        f"- Include category and subcategory to group questions by topic\n"
        f"- Include an explanation for each correct answer\n"
        f"- Output only valid JSON, no markdown or extra text"
    )

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 16000,
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/chat/completions',
        data=payload,
        headers={
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:5001',
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return jsonify({'error': f'OpenRouter API error ({e.code}): {body[:200]}'}), 502
    except (urllib.error.URLError, TimeoutError):
        return jsonify({'error': 'Failed to reach OpenRouter API. Check your connection.'}), 502

    # Extract the content from the response
    try:
        content = result['choices'][0]['message']['content']
    except (KeyError, IndexError):
        return jsonify({'error': 'Unexpected response from OpenRouter API.'}), 502

    # Try to parse JSON from the response (may be wrapped in markdown code blocks)
    json_str = content.strip()
    # Strip markdown code fences if present
    fence_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n```', json_str)
    if fence_match:
        json_str = fence_match.group(1)

    try:
        batch_data = json.loads(json_str)
    except json.JSONDecodeError:
        return jsonify({'error': 'AI returned invalid JSON. Try again or use the copy-prompt method.', 'raw': content[:500]}), 422

    # Validate structure
    if not isinstance(batch_data, dict) or 'questions' not in batch_data:
        return jsonify({'error': 'AI response missing "questions" array. Try again.'}), 422
    if not isinstance(batch_data['questions'], list) or len(batch_data['questions']) == 0:
        return jsonify({'error': 'AI returned empty questions. Try again.'}), 422

    # Sanitize
    valid_letters = {'A', 'B', 'C', 'D'}
    sanitized_questions = []
    for i, q in enumerate(batch_data['questions']):
        if not isinstance(q, dict):
            continue
        if 'id' not in q or 'question' not in q or 'options' not in q or 'correct' not in q:
            continue
        if not isinstance(q['options'], list) or len(q['options']) != 4:
            continue
        if q.get('correct') not in valid_letters:
            continue
        sanitized_questions.append({
            'id': i + 1,
            'category': sanitize_str(str(q.get('category', 'General'))),
            'subcategory': sanitize_str(str(q.get('subcategory', 'General'))),
            'question': sanitize_str(str(q['question'])),
            'options': [sanitize_str(str(o)) for o in q['options']],
            'correct': q['correct'],
            'explanation': sanitize_str(str(q.get('explanation', '')))
        })

    total_raw = len(batch_data.get('questions', []))
    valid_count = len(sanitized_questions)

    if valid_count == 0:
        return jsonify({'error': 'AI output had no valid questions after validation. Try again.'}), 422

    if valid_count < 5:
        return jsonify({'error': f'Only {valid_count} valid questions out of {total_raw}. Too few to be useful — try again.'}), 422

    partial = valid_count < total_raw

    # Keyword verification: check questions are OutSystems-related
    outsystems_match_count = 0
    for q in sanitized_questions:
        text = ' '.join([
            q['question'],
            ' '.join(q['options']),
            q.get('explanation', ''),
            q.get('category', ''),
            q.get('subcategory', ''),
        ]).lower()
        if any(kw in text for kw in OUTSYSTEMS_KEYWORDS):
            outsystems_match_count += 1
    match_ratio = outsystems_match_count / valid_count if valid_count else 0
    if match_ratio < 0.3:
        return jsonify({'error': 'Generated content doesn\'t appear to be OutSystems-related. Try again with a different model.'}), 422

    # Build clean batch
    name = sanitize_str(str(batch_data.get('name', topic)))
    sanitized_data = {
        'name': name,
        'time_limit': 7200,
        'passing_score': 70,
        'questions': sanitized_questions
    }

    # Save batch
    safe_topic = re.sub(r'[^a-zA-Z0-9_-]', '_', topic.lower())[:40]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'generated_{safe_topic}_{timestamp}.json'
    save_batch(filename, sanitized_data)

    BATCHES[filename] = {
        'name': sanitized_data['name'],
        'time_limit': sanitized_data['time_limit'],
        'passing_score': sanitized_data['passing_score'],
        'questions': sanitized_data['questions'],
        'count': len(sanitized_data['questions'])
    }

    session['last_generate'] = datetime.now().isoformat()

    resp = {
        'success': True,
        'key': filename,
        'name': sanitized_data['name'],
        'count': valid_count,
        'cooldown': GENERATE_COOLDOWN
    }
    if partial:
        resp['warning'] = f'{valid_count} of {total_raw} questions were valid. {total_raw - valid_count} were malformed and skipped.'
    return jsonify(resp)


@app.route('/api/upload-batch', methods=['POST'])
def upload_batch():
    """Upload a new question batch JSON file."""
    if not session.get('ui_access'):
        allowed, err = _check_admin_key()
        if not allowed:
            return err

    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    allowed, rate_reason = _check_upload_rate(ip)
    if not allowed:
        return jsonify({'error': rate_reason}), 429

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename or not file.filename.endswith('.json'):
        return jsonify({'error': 'File must be a .json file'}), 400

    # Size check
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_UPLOAD_SIZE:
        return jsonify({'error': 'File too large (max 2MB)'}), 400

    try:
        data = json.load(file)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON'}), 400

    if not isinstance(data, dict):
        return jsonify({'error': 'JSON root must be an object'}), 400
    if 'questions' not in data or not isinstance(data['questions'], list):
        return jsonify({'error': 'Must contain a "questions" array'}), 400
    if len(data['questions']) == 0:
        return jsonify({'error': 'Batch contains no questions'}), 400
    if len(data['questions']) > 500:
        return jsonify({'error': 'Too many questions (max 500)'}), 400

    # Validate and sanitize each question
    valid_letters = {'A', 'B', 'C', 'D'}
    seen_ids = set()
    sanitized_questions = []
    for i, q in enumerate(data['questions']):
        if not isinstance(q, dict):
            return jsonify({'error': f'Question {i+1} is not an object'}), 400
        required = {'id', 'question', 'options', 'correct'}
        missing = required - q.keys()
        if missing:
            return jsonify({'error': f'Question {i+1} missing fields: {missing}'}), 400
        if not isinstance(q['id'], int) or q['id'] < 1:
            return jsonify({'error': f'Question {i+1}: id must be a positive integer'}), 400
        if q['id'] in seen_ids:
            return jsonify({'error': f'Duplicate question id: {q["id"]}'}), 400
        seen_ids.add(q['id'])
        if not isinstance(q['question'], str) or len(q['question'].strip()) == 0:
            return jsonify({'error': f'Question {i+1}: question text is empty'}), 400
        if not isinstance(q['options'], list) or len(q['options']) != 4:
            return jsonify({'error': f'Question {i+1}: must have exactly 4 options'}), 400
        if not all(isinstance(o, str) for o in q['options']):
            return jsonify({'error': f'Question {i+1}: all options must be strings'}), 400
        if q['correct'] not in valid_letters:
            return jsonify({'error': f'Question {i+1}: correct must be A, B, C, or D'}), 400

        sanitized_questions.append({
            'id': q['id'],
            'category': sanitize_str(str(q.get('category', 'General'))),
            'subcategory': sanitize_str(str(q.get('subcategory', 'General'))),
            'question': sanitize_str(q['question']),
            'options': [sanitize_str(o) for o in q['options']],
            'correct': q['correct'],
            'explanation': sanitize_str(str(q.get('explanation', '')))
        })

    # AI content verification — sample questions and check for fabrications
    ai_ok, ai_reason = verify_questions_with_ai(sanitized_questions)
    if not ai_ok:
        return jsonify({'error': f'Content quality check failed: {ai_reason}'}), 400

    # Sanitize batch-level metadata
    name = sanitize_str(str(data.get('name', 'Unnamed Batch')))
    time_limit = data.get('time_limit', 7200)
    passing_score = data.get('passing_score', 70)
    if not isinstance(time_limit, (int, float)) or time_limit < 60 or time_limit > 28800:
        time_limit = 7200
    if not isinstance(passing_score, (int, float)) or passing_score < 1 or passing_score > 100:
        passing_score = 70

    sanitized_data = {
        'name': name,
        'time_limit': int(time_limit),
        'passing_score': int(passing_score),
        'questions': sanitized_questions
    }

    filename = secure_filename(file.filename)
    if not filename or filename == '':
        filename = 'upload.json'
    save_batch(filename, sanitized_data)

    BATCHES[filename] = {
        'name': sanitized_data['name'],
        'time_limit': sanitized_data['time_limit'],
        'passing_score': sanitized_data['passing_score'],
        'questions': sanitized_data['questions'],
        'count': len(sanitized_data['questions'])
    }

    return jsonify({'success': True, 'key': filename, 'name': sanitized_data['name'], 'count': len(sanitized_data['questions'])})

@app.route('/exam')
def index():
    """Initialize exam session"""
    reload_batches()
    batch_key = request.args.get('batch')
    if batch_key and batch_key in BATCHES:
        batch = BATCHES[batch_key]
        ids = [q['id'] for q in batch['questions']]
        session['batch_key'] = batch_key
        session['question_order'] = ids
        session['start_time'] = datetime.now().isoformat()
        session['answers'] = {}
        session['flagged'] = []
        session['time_limit'] = batch['time_limit']
        session['passing_score'] = batch['passing_score']
        session['o11_only_questions'] = {str(k): v for k, v in batch.get('o11_only_questions', {}).items()}
        return render_template('index.html')
    elif 'batch_key' in session and session['batch_key'] in BATCHES:
        return render_template('index.html')
    else:
        return redirect('/')

@app.route('/api/questions')
def get_questions():
    """Get all questions without answers"""
    o11_map = session.get('o11_only_questions', {})
    questions_for_client = []
    for q in get_session_questions():
        q_id = str(q['id'])
        questions_for_client.append({
            'id': q['id'],
            'category': q['category'],
            'subcategory': q['subcategory'],
            'question': q['question'],
            'options': q['options'],
            'is_o11': q_id in o11_map,
            'o11_note': o11_map.get(q_id, ''),
        })
    return jsonify(questions_for_client)

@app.route('/api/submit', methods=['POST'])
def submit_exam():
    """Grade exam and return results"""
    data = request.get_json()
    user_answers = data.get('answers', {})

    questions = get_session_questions()
    o11_map = session.get('o11_only_questions', {})
    score = 0
    results = []

    for question in questions:
        q_id = str(question['id'])
        user_answer = user_answers.get(q_id, '')
        is_correct = user_answer == question['correct']

        if is_correct:
            score += 1

        results.append({
            'id': question['id'],
            'category': question['category'],
            'subcategory': question['subcategory'],
            'question': question['question'],
            'options': question['options'],
            'correct': question['correct'],
            'user_answer': user_answer,
            'is_correct': is_correct,
            'is_o11': q_id_str in o11_map,
            'o11_note': o11_map.get(q_id_str, ''),
        })

    percentage = (score / len(questions)) * 100
    passed = percentage >= session.get('passing_score', 70)

    category_breakdown = {}
    for result in results:
        cat = result['category']
        if cat not in category_breakdown:
            category_breakdown[cat] = {'total': 0, 'correct': 0}
        category_breakdown[cat]['total'] += 1
        if result['is_correct']:
            category_breakdown[cat]['correct'] += 1

    return jsonify({
        'score': score,
        'total': len(questions),
        'percentage': round(percentage, 1),
        'passed': passed,
        'results': results,
        'category_breakdown': category_breakdown
    })

@app.route('/api/save-answer', methods=['POST'])
def save_answer():
    """Save user's answer"""
    data = request.get_json()
    q_id = str(data.get('question_id'))
    answer = data.get('answer')

    if 'answers' not in session:
        session['answers'] = {}

    answers = session['answers']
    answers[q_id] = answer
    session['answers'] = answers
    session.modified = True

    return jsonify({'success': True})

@app.route('/api/toggle-flag', methods=['POST'])
def toggle_flag():
    """Toggle question flag"""
    data = request.get_json()
    q_id = str(data.get('question_id'))

    if 'flagged' not in session:
        session['flagged'] = []

    flagged = list(session['flagged'])
    if q_id in flagged:
        flagged.remove(q_id)
    else:
        flagged.append(q_id)
    session['flagged'] = flagged
    session.modified = True

    return jsonify({'flagged': q_id in session['flagged']})

@app.route('/api/time-remaining')
def time_remaining():
    """Get remaining exam time"""
    time_limit = session.get('time_limit', 7200)
    if 'start_time' not in session:
        return jsonify({'remaining': time_limit})

    start = datetime.fromisoformat(session['start_time'])
    elapsed = (datetime.now() - start).total_seconds()
    remaining = max(0, time_limit - elapsed)

    return jsonify({'remaining': remaining})

@app.route('/reset')
def reset():
    """Reset exam session"""
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = not os.environ.get('REPL_ID')  # debug off on Replit
    app.run(host='0.0.0.0', port=port, debug=debug)
