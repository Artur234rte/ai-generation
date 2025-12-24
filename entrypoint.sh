#!/usr/bin/env sh
set -eu

attempts=0
until alembic upgrade head; do
  attempts=$((attempts + 1))
  if [ "$attempts" -ge 10 ]; then
    echo "Failed to apply migrations after $attempts attempts, exiting"
    exit 1
  fi
  echo "Database not ready yet, retrying ($attempts)..."
  sleep 2
done

exec "$@"
