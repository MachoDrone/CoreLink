#!/bin/bash
set -e

# ---- TLS certificate setup ----
CERT_DIR="/data/ssl"
mkdir -p "$CERT_DIR"

if [ -f "$CERT_DIR/cert.pem" ] && [ -f "$CERT_DIR/key.pem" ]; then
    echo "[CoreLink] Using existing TLS certificate."
    if [ -f "$CERT_DIR/ca.pem" ]; then
        echo "[CoreLink] CA-signed certificate detected."
    fi
else
    # Fallback: generate self-signed cert (legacy mode / manual docker run)
    echo "[CoreLink] No certificate found. Generating self-signed TLS certificate..."
    HOSTNAME="${CORELINK_HOSTNAME:-$(hostname)}"
    openssl req -x509 -newkey rsa:4096 \
        -keyout "$CERT_DIR/key.pem" \
        -out "$CERT_DIR/cert.pem" \
        -days 3650 -nodes \
        -subj "/CN=${HOSTNAME}/O=CoreLink" \
        2>/dev/null
    echo "[CoreLink] Self-signed certificate generated."
fi

# ---- Generate Flask secret key (persists across restarts) ----
SECRET_FILE="/data/secret_key"
if [ ! -f "$SECRET_FILE" ]; then
    python3 -c "import os; open('$SECRET_FILE','w').write(os.urandom(32).hex())"
fi

# ---- Start CoreLink ----
PORT="${CORELINK_PORT:-443}"
echo "[CoreLink] Starting on port ${PORT}..."
exec python3 /app/server.py --port "$PORT"
