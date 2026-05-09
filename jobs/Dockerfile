FROM python:3.11-slim

WORKDIR /app

# Installera systemberoenden för psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Kopiera projektfiler
COPY pyproject.toml .
COPY ingestion/ ingestion/
COPY transformation/ transformation/
COPY ml_model/ ml_model/
COPY jobs/ jobs/

# Installera projektberoenden (utan dev-extras)
RUN pip install --no-cache-dir -e "."

# Kör runner
CMD ["python", "-m", "jobs.runner"]
