FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir ".[dev]" streamlit plotly

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/dashboard.py", "--server.address", "0.0.0.0"]
