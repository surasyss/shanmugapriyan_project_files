#!/bin/bash
set -e

echo "[entrypoint] Entered entrypoint"

. /app/bin/activate

spicli aws get-secrets --names "$ENV_CONFIG" --output secrets.sh
if [ -f "secrets.sh" ]; then
  . secrets.sh
fi

exec "$@"

echo "[entrypoint] Exiting"
