#!/usr/bin/env python3
"""Cloud Run entrypoint for MLflow server.

Uses base64-decoded password to safely handle any special characters
(backticks, pipes, quotes, etc.) that would break shell-based entrypoints.
"""
import base64
import os
import urllib.parse


def main() -> None:
    user = os.environ.get("POSTGRES_USER", "")
    host = os.environ.get("POSTGRES_HOST", "")
    bucket = os.environ.get("MLFLOW_ARTIFACT_BUCKET", "")
    port = os.environ.get("PORT", "5000")

    # POSTGRES_PASSWORD_B64 is base64-encoded to survive --set-env-vars parsing.
    # Falls back to plain POSTGRES_PASSWORD for local/legacy use.
    password_b64 = os.environ.get("POSTGRES_PASSWORD_B64", "")
    if password_b64:
        password = base64.b64decode(password_b64).decode("utf-8")
    else:
        password = os.environ.get("POSTGRES_PASSWORD", "")

    encoded_password = urllib.parse.quote(password, safe="")
    db_uri = f"postgresql+psycopg2://{user}:{encoded_password}@{host}:5432/mlflow"

    print(f"Starting MLflow on port {port}, backend: postgresql@{host}/mlflow", flush=True)

    os.execvp(
        "mlflow",
        [
            "mlflow",
            "server",
            "--host",
            "0.0.0.0",
            "--port",
            port,
            "--backend-store-uri",
            db_uri,
            "--artifacts-destination",
            f"gs://{bucket}",
            "--serve-artifacts",
            "--allowed-hosts",
            "*",
        ],
    )


if __name__ == "__main__":
    main()
