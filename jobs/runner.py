"""
Cloud Run Jobs runner.

Läser JOB_NAME från miljövariabeln och kör rätt pipeline-steg.
Körs som ett engångsjobb i GCP Cloud Run Jobs.
"""

import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

JOB_NAME = os.environ.get("JOB_NAME", "")

VALID_JOBS = ["smhi-ingestion", "trafikverket-ingestion", "transformation", "ml-training"]

if not JOB_NAME:
    logger.error("JOB_NAME saknas. Sätt env-variabeln JOB_NAME.")
    sys.exit(1)

if JOB_NAME not in VALID_JOBS:
    logger.error("Okänt job: %s. Giltiga: %s", JOB_NAME, VALID_JOBS)
    sys.exit(1)

logger.info("Startar job: %s", JOB_NAME)

if JOB_NAME == "smhi-ingestion":
    from ingestion.smhi.ingest_smhi import run_ingestion
    result = run_ingestion()
    logger.info("SMHI-ingestion klar: %s", result)

elif JOB_NAME == "trafikverket-ingestion":
    from ingestion.trafikverket.ingest_trafikverket import run_ingestion
    result = run_ingestion()
    logger.info("Trafikverket-ingestion klar: %s", result)

elif JOB_NAME == "transformation":
    from transformation.transform_and_merge import run_transformation
    result = run_transformation()
    logger.info("Transformation klar: %s", result)

elif JOB_NAME == "ml-training":
    from ml_model.train import run_training
    result = run_training()
    logger.info(
        "ML-träning klar: status=%s version=%s R²=%.3f",
        result["status"],
        result["version"],
        result["r2"],
    )
