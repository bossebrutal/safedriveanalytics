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
| S2-1 | Som ML-team vill vi ha sammanslagen data | Bygg transform + feature engineering | - | 🔄 In Progress | 8 |
| S2-2 | Som slutanvändare vill jag kunna göra prediktioner | Bygg FastAPI + ML-modell | - | ✅ Done | 8 |
| S2-3 | Som team vill vi ha CI/CD | GitHub Actions CI + CD till Cloud Run | - | ✅ Done | 5 |
| S2-4 | Som analytiker vill jag se insikter | Bygg Streamlit-dashboard | - | 🔄 In Progress | 5 |

---

# Sprint 3 – Planering

**Period:** Vecka 5–6  
**Mål:** Allt deployat i molnet, presentationsförberedelse

| ID | User Story | Uppgift | Status | Poäng |
|----|-----------|---------|--------|-------|
| S3-1 | Driftsätt allt på GCP | Cloud Run deploy + Cloud SQL | ⬜ Todo | 8 |
| S3-2 | Verifiera Airflow i molnet | Cloud Composer eller Airflow på Cloud Run | ⬜ Todo | 8 |
| S3-3 | Presentationsslides | Slides med demo, arkitektur, agilt arbete | ⬜ Todo | 3 |
| S3-4 | A4-dokument | Metodbeskrivning och verktygsval | ⬜ Todo | 2 |
