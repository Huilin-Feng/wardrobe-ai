FROM python:3.13-slim

# Don't write .pyc files; print logs immediately instead of buffering them.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Dependencies first, code second: Docker caches each step, so editing the code
# does not trigger a slow reinstall of every package.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Run as an unprivileged user rather than root.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p uploads data \
    && chown -R appuser:appuser /code
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]