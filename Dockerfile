FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# migrate and collectstatic run at deploy time (they need env/DB), not at build:
#   python manage.py migrate && python manage.py collectstatic --noinput
CMD ["gunicorn", "leavehub.wsgi:application", "--bind", "0.0.0.0:8000"]
