"""Minimal runnable API bootstrap. Feature owners will extend it in their PRs."""
import os

from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="Alfa Business News Analytics — bootstrap API",
    version="0.1.0",
    description="Infrastructure smoke-test API; business insights are NOT implemented yet.",
)


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    """Verify that API can reach PostgreSQL (not just that HTTP is listening)."""
    try:
        import psycopg
        with psycopg.connect(
            host=os.environ["DB_HOST"],
            port=int(os.environ.get("DB_PORT", "5432")),
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            connect_timeout=3,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception:
        # Avoid returning connection strings or database credentials.
        raise HTTPException(status_code=503, detail="database_unavailable") from None
    return {"status": "ok", "database": "ok"}


@app.get("/api/v1/companies", tags=["companies"])
def list_companies() -> dict[str, object]:
    """Placeholder until the data owner connects synthetic companies."""
    return {"items": [], "total": 0}
