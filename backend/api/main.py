
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from data.initilization.init_db import engine
from data.models.models import Base


app = FastAPI(title="BITochkiAPI", description="First step api", version="1.0")

origins = [
] # когда фронт что-то сделают, то я сюда добавлю что-то

app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def init_db():
    Base.metadata.create_all(bind=engine)


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    try:
        init_db()
    except Exception:
        raise HTTPException(status_code=503, detail="database_unavailable") from None
    return {"status": "ok", "database": "ok"}
