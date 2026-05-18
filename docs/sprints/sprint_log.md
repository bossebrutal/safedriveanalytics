# Sprint 1 – Dokumentation

**Projekt:** SafeDrive Analytics  
**Sprint:** 1 av 3  
**Period:** Vecka 1–2  
**Mål:** Grundläggande infrastruktur och ingestion-pipelines fungerar lokalt

## Sprint Backlog

| ID | User Story | Uppgift | Ansvarig | Status | Poäng |
|----|-----------|---------|----------|--------|-------|
| S1-1 | Som team vill vi ha ett fungerande dev-env | Sätt upp repo, docker-compose, `.env` | Alla | ✅ Done | 3 |
| S1-2 | Som datateam vill vi kunna hämta väderdata | Bygg SMHI-klient + ingestion pipeline | - | ✅ Done | 5 |
| S1-3 | Som datateam vill vi kunna hämta trafikdata | Bygg Trafikverket-klient + ingestion pipeline | - | ✅ Done | 5 |
| S1-4 | Som datateam vill vi ha en databas | Skapa PostgreSQL-schema | - | ✅ Done | 2 |
| S1-5 | Som team vill vi ha automatiska tester | Skriv enhetstester för ingestion-klienter | - | ✅ Done | 3 |

**Sprint velocity:** 18 poäng

## Retrospektiv

**Vad gick bra:**
- Snabb uppstart med docker-compose
- SMHI API är välstrukturerat och gratis
- Trafikverkets API kräver registrering men är bra dokumenterat

**Vad kan förbättras:**
- Behöver lägga till fler integrationstester nästa sprint

---

# Sprint 2 – Planering

**Period:** Vecka 3–4  
**Mål:** Transformation, ML-modell och API deployat

| ID | User Story | Uppgift | Ansvarig | Status | Poäng |
|----|-----------|---------|----------|--------|-------|
| S2-1 | Som ML-team vill vi ha sammanslagen data | Bygg transform + feature engineering | - | ✅ Done | 8 |
| S2-2 | Som slutanvändare vill jag kunna göra prediktioner | Bygg FastAPI + ML-modell | - | ✅ Done | 8 |
| S2-3 | Som team vill vi ha CI/CD | GitHub Actions CI + CD till Cloud Run | - | ✅ Done | 5 |
| S2-4 | Som analytiker vill jag se insikter | Bygg Streamlit-dashboard med prediktion + MLflow-metrics | - | ✅ Done | 5 |

**Sprint velocity:** 26 poäng

## Retrospektiv

**Vad gick bra:**
- MLflow model registry med champion/challenger-promotion fungerar som avsett
- Airflow-schemat (DAG) tränar modellen automatiskt varje timme med ny data
- FastAPI laddar om champion-modellen i bakgrunden (zero-downtime)
- R² förbättrades från 0.247 (dag 1, v1) till 0.362 (dag 2, v16) i takt med mer data
- Dashboarden visar nu live-prediktion, träningshistorik och modellprestanda

**Vad kan förbättras:**
- GCP-deploy saknas fortfarande – molndrift är nästa sprint
- Feature engineering kan utökas (t.ex. helgdagsindikator, säsong)

---

# Sprint 3 – Planering

**Period:** Vecka 5–6  
**Mål:** Allt deployat i molnet, presentationsförberedelse

| ID | User Story | Uppgift | Status | Poäng |
|----|-----------|---------|--------|-------|
| S3-1 | Driftsätt allt på GCP | Cloud Run deploy + Cloud SQL + MLflow 2Gi | ✅ Done | 8 |
| S3-2 | Pipeline i molnet | Cloud Run Jobs + Cloud Scheduler (4 schemalagda jobb) | ✅ Done | 8 |
| S3-3 | Presentationsslides | Slides med demo, arkitektur, agilt arbete | ✅ Done | 3 |
| S3-4 | A4-dokument | Metodbeskrivning och verktygsval | ✅ Done | 2 |

## Uppnått i S3-1
- ✅ MLflow på Cloud Run (2Gi RAM, GCS artifacts, Cloud SQL backend)
- ✅ FastAPI + Streamlit på Cloud Run
- ✅ Cloud SQL (europe-north1) med 4 tabeller, 995 rader ml_features
- ✅ CI/CD pipeline: CI på alla branches, CD bara på main
- ✅ Airflow DAGs pekar på Cloud SQL + Cloud Run MLflow
- ✅ SafeDriveModel tränad och registrerad i MLflow (R²=0.136, 995 rader)
- ✅ Modell-artefakter i GCS bucket `safedriveanalytics-mlflow-artifacts`

## Uppnått i S3-2
- ✅ `jobs/runner.py` – dispatcher som kör rätt pipeline-steg via JOB_NAME env-var
- ✅ `jobs/Dockerfile` – bygger delad image för alla pipeline-jobb
- ✅ 4 Cloud Run Jobs deployade (europe-north1):
  - `pipeline-smhi-ingestion`
  - `pipeline-trafikverket-ingestion`
  - `pipeline-transformation`
  - `pipeline-ml-training`
- ✅ 4 Cloud Scheduler-scheman (europe-west1):
  - SMHI: varje timme :00
  - Trafikverket: var 15:e minut
  - Transformation: varje timme :10
  - ML-träning: dagligen kl 02:00
- ✅ IAM: Cloud Scheduler Admin-roll tillagd för github-actions SA

## Uppnått i S3-3 & S3-4
- ✅ Presentationsslides skapade (PPTX med 8 slides, manus i docs/)
- ✅ A4-projektbeskrivning genererad (docs/projektbeskrivning_a4.docx)
- ✅ Zippad kod inkl. .git-mapp (safedriveanalytics_submission.zip)
- ✅ Bugfix: pipeline-ml-training minnesgräns höjd till 2Gi (OOM-fix i cd.yml)
- ✅ ML-modell tränad och registrerad i MLflow (R²=0.342, v4)

**Sprint velocity:** 21 poäng

## Retrospektiv

**Vad gick bra:**
- Hela systemet körs i GCP med automatiska schemalagda pipelines
- Champion/challenger-logik fungerar – modellen förbättras med mer data
- CI/CD-flödet från push till deploy fungerar utan manuella steg

**Vad kan förbättras:**
- ML-träningsjobbet behövde mer RAM än ursprungligen allokerat (512Mi → 2Gi)
- Fler features (t.ex. helgdagsindikator) skulle förbättra modellens R²
