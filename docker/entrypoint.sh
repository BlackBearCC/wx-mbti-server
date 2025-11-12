#!/bin/sh
set -e

HOST="0.0.0.0"
PORT="8000"
APP_IMPORT="app.main:app"

CERT_DIR=${SSL_CERT_DIR:-/app/certs}
CERT_FILE=${SSL_CERTFILE:-}
KEY_FILE=${SSL_KEYFILE:-}

# Auto-detect cert pair if not provided
if [ -z "$CERT_FILE" ] || [ -z "$KEY_FILE" ]; then
  if [ -d "$CERT_DIR" ]; then
    # Prefer mkcert-style filenames, else pick first .pem pair
    CAND_CERT=$(ls "$CERT_DIR"/*.pem 2>/dev/null | head -n1 || true)
    CAND_KEY=$(ls "$CERT_DIR"/*-key.pem 2>/dev/null | head -n1 || true)
    if [ -n "$CAND_CERT" ] && [ -n "$CAND_KEY" ]; then
      CERT_FILE="$CAND_CERT"
      KEY_FILE="$CAND_KEY"
    fi
  fi
fi

if [ -n "$CERT_FILE" ] && [ -n "$KEY_FILE" ] && [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
  echo "[INFO] Starting Uvicorn with TLS: https://$HOST:$PORT"
  exec uvicorn "$APP_IMPORT" --host "$HOST" --port "$PORT" \
    --ssl-certfile "$CERT_FILE" --ssl-keyfile "$KEY_FILE"
else
  echo "[ERR] TLS cert/key not found. Please mount certs into $CERT_DIR or set SSL_CERTFILE/SSL_KEYFILE."
  echo "      Example (mkcert): mkcert -install && mkcert localhost 127.0.0.1; then mount to ./.cert -> /app/certs"
  exit 1
fi

