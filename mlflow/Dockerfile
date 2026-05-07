FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir mlflow psycopg2-binary google-cloud-storage

COPY mlflow/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000
CMD ["/entrypoint.sh"]
