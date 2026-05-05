# SafeDrive Analytics

**SafeDrive Analytics AB** – ett datadrivet projekt som analyserar hur väder påverkar trafikflödet i Sverige.

## Datakällor
- **SMHI Open Data API** – Väderobservationer (temperatur, nederbörd, vind, sikt)
- **Trafikverket API** – Trafikflöde, hastigheter och incidenter i realtid

## Arkitektur

```
SMHI API ──────┐
               ├─► Airflow (ingest → transform → load) ─► PostgreSQL ─► ML Model ─► FastAPI ─► End User
Trafikverket ──┘                                                         │
                                                                          └─► Dashboard (Streamlit)
```

## Komponenter

| Komponent | Teknologi | Syfte |
|-----------|-----------|-------|
| Orchestration | Apache Airflow | Schemalagda pipelines |
| Ingestion | Python + requests | Hämta data från API:er |
| Lagring | PostgreSQL | Strukturerad datalagring |
| Transformation | Python (pandas) | Rensa & berika data |
| ML Model | scikit-learn | Prediktera trafikpåverkan |
| Serving | FastAPI | REST API för modellen |
| Dashboard | Streamlit | Visualisering & insikter |
| CI/CD | GitHub Actions | Autotest + linting + deploy |
| Containerisering | Docker + docker-compose | Isolerade tjänster |

## Kom igång

### Förutsättningar
- Docker & Docker Compose
- Python 3.11+
- Trafikverket API-nyckel (registrera gratis på [trafikinfo.trafikverket.se](https://api.trafikinfo.trafikverket.se))

### Konfiguration
```bash
cp .env.example .env
# Fyll i din TRAFIKVERKET_API_KEY i .env
```

### Starta allt
```bash
docker-compose up -d
```

Airflow UI: http://localhost:8080  
API: http://localhost:8000  
Dashboard: http://localhost:8501  

### Kör tester
```bash
pip install -e ".[dev]"
pytest
```

### Linting
```bash
ruff check .
```

## Projektstruktur
```
safedriveanalytics/
├── airflow/
│   ├── dags/              # Airflow DAGs (schemalagda pipelines)
│   └── Dockerfile
├── ingestion/
│   ├── smhi/              # SMHI API-klient + tester
│   └── trafikverket/      # Trafikverket API-klient + tester
├── transformation/        # Datarensning & feature engineering
├── ml_model/              # Träning + prediktion
├── api/                   # FastAPI-server för ML-modellen
├── dashboard/             # Streamlit-dashboard
├── database/              # SQL-schema
├── .github/workflows/     # CI/CD pipelines
└── docker-compose.yml
```

## Agilt arbetsflöde
Projektet använder Kanban-tavla (GitHub Projects) med följande kolumner:
- **Backlog** → **In Progress** → **Review** → **Done**

Sprints dokumenteras i `docs/sprints/`.
