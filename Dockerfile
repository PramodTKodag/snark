FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential libpq-dev curl netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && pip install poetry && poetry config virtualenvs.create false

COPY pyproject.toml README.md ./
COPY snark ./snark

RUN poetry install --no-interaction --no-ansi -v

RUN mkdir -p /app/staticfiles && cd /app/snark && \
    POSTGRES_PASSWORD=build POSTGRES_USER=build POSTGRES_DB=build POSTGRES_HOST=localhost \
    SECRET_KEY=build-only-key \
    python manage.py collectstatic --noinput

EXPOSE 8094

CMD ["sh", "-c", "cd snark && python manage.py migrate && gunicorn base.wsgi:application --bind 0.0.0.0:8094 --workers 2 --threads 2 --max-requests 1000 --max-requests-jitter 100 --timeout 120"]
