#!/usr/bin/env sh
# Render start command: prepare the database and static files, then serve.
set -e

python manage.py migrate
python manage.py createcachetable
python manage.py collectstatic --noinput

# Reseed the demo org on every boot so the public demo stays clean (SEED_ON_BOOT=true)
if [ "$SEED_ON_BOOT" = "true" ]; then
    python manage.py seed_demo --reset
fi

exec gunicorn leavehub.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
