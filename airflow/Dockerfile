FROM apache/airflow:2.9.1-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

USER airflow
COPY airflow/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Kopiera in projektkod så att DAGar kan importera ingestion/transformation
COPY --chown=airflow:root . /opt/airflow/project
ENV PYTHONPATH=/opt/airflow/project
