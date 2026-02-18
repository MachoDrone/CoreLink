"""CoreLink - PAM authentication and Flask-Login integration."""

import time
import threading

import pam
from flask_login import UserMixin


# ---------------------------------------------------------------------------
# User model for Flask-Login
# ---------------------------------------------------------------------------

class User(UserMixin):
    """Thin wrapper around a Linux username for Flask-Login."""

    def __init__(self, username):
        self.id = username
        self.username = username


# ---------------------------------------------------------------------------
# PAM authentication
# ---------------------------------------------------------------------------

def authenticate_pam(username, password):
    """Authenticate *username* / *password* against the host PAM stack.

    Returns True on success, False otherwise.  The container must have
    /etc/passwd and /etc/shadow bind-mounted read-only from the host.
    """
    try:
        p = pam.pam()
        return p.authenticate(username, password, service="login")
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Simple rate-limiting  (per-IP, in-memory)
# ---------------------------------------------------------------------------

_MAX_FAILURES = 5
_COOLDOWN_SECONDS = 30

_lock = threading.Lock()
_failures = {}  # {ip: (count, last_failure_time)}


def check_rate_limit(client_ip):
    """Return True if the client IP is allowed to attempt login."""
    with _lock:
        entry = _failures.get(client_ip)
        if entry is None:
            return True
        count, last_time = entry
        if count >= _MAX_FAILURES:
            if time.time() - last_time < _COOLDOWN_SECONDS:
                return False
            # Cooldown expired — reset
            del _failures[client_ip]
        return True


def record_failure(client_ip):
    """Record a failed login attempt from *client_ip*."""
    with _lock:
        entry = _failures.get(client_ip)
        if entry is None:
            _failures[client_ip] = (1, time.time())
        else:
            count, _ = entry
            _failures[client_ip] = (count + 1, time.time())
