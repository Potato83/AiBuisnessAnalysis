from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BITochkiAPI", description="First step api", version="1.0")

origins = [
] #когда фронт что-то сделают, то я сюда добавлю что-то

app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


