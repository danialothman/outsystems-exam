"""
Storage abstraction for question batches.
Auto-detects environment: uses Replit App Storage on Replit, local filesystem otherwise.
"""
import json
import os
import glob as glob_mod
import logging

logger = logging.getLogger(__name__)

QUESTIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'questions')
IS_REPLIT = bool(os.environ.get('REPL_ID'))

_replit_client = None


def _get_replit_client():
    global _replit_client
    if _replit_client is None:
        from replit.object_storage import Client
        _replit_client = Client()
    return _replit_client


def _parse_batch(filename, data):
    """Parse a batch dict from raw JSON data."""
    return {
        'name': data.get('name', filename),
        'time_limit': data.get('time_limit', 7200),
        'passing_score': data.get('passing_score', 70),
        'questions': data['questions'],
        'count': len(data['questions']),
        'o11_only_questions': data.get('o11_only_questions', {}),
    }


def load_all_batches():
    """Load all question batches. Returns dict of filename -> batch data."""
    batches = {}

    # Always load from local questions/ folder (git-committed batches)
    os.makedirs(QUESTIONS_DIR, exist_ok=True)
    for filepath in sorted(glob_mod.glob(os.path.join(QUESTIONS_DIR, '*.json'))):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            filename = os.path.basename(filepath)
            batches[filename] = _parse_batch(filename, data)
        except (json.JSONDecodeError, KeyError):
            continue

    # On Replit, also load from App Storage
    if IS_REPLIT:
        try:
            client = _get_replit_client()
            objects = client.list()
            for obj in objects:
                name = obj.name if hasattr(obj, 'name') else str(obj)
                if not name.endswith('.json'):
                    continue
                if name in batches:
                    continue  # local files take priority
                try:
                    content = client.download_as_text(name)
                    data = json.loads(content)
                    batches[name] = _parse_batch(name, data)
                except Exception as e:
                    logger.warning(f'[storage] Failed to load {name} from bucket: {e}')
                    continue
        except Exception as e:
            logger.error(f'[storage] Could not connect to bucket: {e}')

    return batches


def save_batch(filename, data):
    """Save a batch JSON. Writes to App Storage on Replit, local filesystem otherwise."""
    json_str = json.dumps(data, indent=2)

    if IS_REPLIT:
        try:
            client = _get_replit_client()
            client.upload_from_text(filename, json_str)
            logger.info(f'[storage] Saved {filename} to bucket OK')
            return
        except Exception as e:
            logger.error(f'[storage] Bucket save FAILED for {filename}: {e} — falling back to local disk (will not persist across deploys)')

    # Local filesystem save
    os.makedirs(QUESTIONS_DIR, exist_ok=True)
    filepath = os.path.join(QUESTIONS_DIR, filename)
    with open(filepath, 'w') as f:
        f.write(json_str)
    logger.info(f'[storage] Saved {filename} to local disk')
