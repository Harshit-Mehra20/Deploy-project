from flask import Blueprint, request, jsonify, make_response
import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone

from db.database import find_user_by_email, create_user

auth_bp = Blueprint('auth', __name__)

# Secret key for JWT — use an env var in production
JWT_SECRET = os.environ.get('JWT_SECRET', 'deepdetect_jwt_secret_2026')


@auth_bp.after_request
def add_cors(response):
    """Ensure every auth response carries CORS headers.
    Browsers send Origin: null when the page is loaded via file://.
    Setting * covers both that and normal localhost origins.
    """
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response


@auth_bp.route('/api/signup', methods=['OPTIONS'])
@auth_bp.route('/api/login',  methods=['OPTIONS'])
def preflight(*args, **kwargs):
    """Handle CORS preflight requests."""
    resp = make_response('', 204)
    resp.headers['Access-Control-Allow-Origin']  = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    resp.headers['Access-Control-Allow-Methods'] = 'POST,OPTIONS'
    return resp


def _make_token(user_id: int, email: str) -> str:
    payload = {
        'sub': user_id,
        'email': email,
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def _user_to_dict(user) -> dict:
    return {
        'id':          user['id'],
        'name':        user['name'],
        'email':       user['email'],
        'plan':        user['plan'],
        'trial_start': user['trial_start'],
    }


@auth_bp.route('/api/signup', methods=['POST'])
def signup():
    data     = request.get_json(silent=True) or {}
    name     = (data.get('name')     or '').strip()
    email    = (data.get('email')    or '').strip().lower()
    password =  data.get('password') or ''

    if not name or not email or not password:
        return jsonify({'success': False, 'error': 'All fields are required'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

    if find_user_by_email(email):
        return jsonify({'success': False, 'error': 'Email already registered'}), 409

    # Hash password
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    user_id = create_user(name, email, pw_hash)
    user    = find_user_by_email(email)
    token   = _make_token(user_id, email)

    return jsonify({
        'success': True,
        'token':   token,
        'user':    _user_to_dict(user)
    }), 201


@auth_bp.route('/api/login', methods=['POST'])
def login():
    data     = request.get_json(silent=True) or {}
    email    = (data.get('email')    or '').strip().lower()
    password =  data.get('password') or ''

    if not email or not password:
        return jsonify({'success': False, 'error': 'Email and password required'}), 400

    user = find_user_by_email(email)
    if not user:
        return jsonify({'success': False, 'error': 'Invalid email or password'}), 401

    if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        return jsonify({'success': False, 'error': 'Invalid email or password'}), 401

    # Check trial expiry — both datetimes kept naive (UTC) for consistent comparison
    try:
        trial_start = datetime.fromisoformat(user['trial_start'])
    except (ValueError, TypeError):
        trial_start = datetime.now(timezone.utc).replace(tzinfo=None)

    now          = datetime.utcnow()   # naive UTC, matches SQLite datetime('now')
    days_elapsed = (now - trial_start).days
    trial_expired = days_elapsed >= 7 and user['plan'] == 'trial'

    token = _make_token(user['id'], email)

    return jsonify({
        'success':      True,
        'token':        token,
        'user':         _user_to_dict(user),
        'trialExpired': trial_expired
    })
