from fastapi import FastAPI
from app.models import Provider

app = FastAPI(title="Integration Aggregator")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {"status": "ready"}

@app.post("/providers")
def register_provider(provider:Provider):
    return {
        "message":"Provider registered",
        "provider":provider.name
    }