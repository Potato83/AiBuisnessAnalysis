# API contract v0.1 — Alfa Hack news analytics

**Base path:** `/api/v1`; transport HTTPS in publicly reachable environments; JSON UTF-8.
This is an **agreed-proposal baseline for team review**, not a claim that all endpoints are implemented.

## Implemented by the DevOps bootstrap

| Method/path | 200 response | Notes |
|---|---|---|
| `GET /api/v1/health` | `{"status":"ok","database":"ok"}` | Database error = 503 with `{"detail":"database_unavailable"}` |
| `GET /api/v1/companies` | `{"items":[],"total":0}` | Empty until synthetic company fixtures are imported |

The bootstrap health endpoint queries PostgreSQL. API's generated OpenAPI UI is at `/docs` on the backend container (not exposed through Nginx yet).

## Planned endpoints (owners implement via feature PRs)

| Method/path | Owner | Input | Output |
|---|---|---|---|
| `GET /api/v1/companies` | Data + Backend | `limit`, `offset` (optional) | `CompanyList` |
| `GET /api/v1/companies/{company_id}` | Data + Backend | `company_id` | `Company` |
| `GET /api/v1/companies/{company_id}/insights` | Backend + AI | `company_id`, optional `limit` | `InsightList` ranked for company |
| `GET /api/v1/insights/{insight_id}` | Backend + AI | `insight_id` | `Insight` incl. provenance |
| `POST /api/v1/insights/{insight_id}/ask` | AI + Backend | `{"question":"..."}` | `Answer` with citations, run ID |

**IDs:** opaque strings. **Times:** ISO 8601 UTC. **All monetary values:** decimal string + explicit currency. Avoid fake certainty for speculative business effects.

### Data shapes for implementation

```json
{
  "company": {
    "id": "synthetic-u-0001",
    "name": "Synthetic Enterprise One",
    "industry_code": "46.90",
    "industry_name": "Wholesale trade",
    "region": "Moscow",
    "revenue_rub": "17000000000",
    "has_loans": true,
    "counterparty_ids": ["synthetic-u-0002"]
  },
  "insight": {
    "id": "insight-001",
    "company_id": "synthetic-u-0001",
    "event_id": "event-101",
    "headline": "Illustrative event",
    "why_relevant": "Potential loan cost exposure",
    "impact": "Scenario-based, not a confirmed outcome",
    "risks": ["Financing costs could remain high"],
    "opportunities": [],
    "bank_view": "Attributed analyst statement if supplied",
    "ai_interpretation": "Model-generated scenario, explicitly labeled",
    "confidence": "medium",
    "sources": [
      {"id":"src-1","title":"Illustrative source","url":"https://example.org/source","kind":"external_news","published_at":"2026-10-01T12:00:00Z"}
    ],
    "agent_run_id": "run-1",
    "generated_at": "2026-10-21T12:00:00Z"
  },
  "answer": {
    "answer":"...",
    "sources":["src-1"],
    "agent_run_id":"run-2"
  }
}
```

The JSON above is **only a schema example with fictional data**, not actual collected news or model output.

### Errors

- `400` invalid request; `404` not found; `422` FastAPI validation; `503` temporary infrastructure / model unavailable.
- JSON errors use `{"detail":"human-or-machine-readable-message"}`. Agent and AI integration should later introduce stable error codes.

### Responsibility boundary

- Frontend calls only relative `/api/v1/...`, never internal Docker hostname; Nginx routes API requests.
- Backend owns request validation, persistence interfaces, response formats and authentication integration.
- Data owns synthetic company ingestion, source metadata, news normalization and deduplication.
- AI owns planning, tool invocation, evidence trace, constrained-model selection, budget limiting, self-check and answer generation.
- TeamLead/DevOps owns Compose, CI, secrets handling, environment lifecycle and deployment.

**Before merging feature PRs:** review field names with all five participants; don't break this contract without documenting migration and updating consumers.
