from fastapi import FastAPI, HTTPException

from app.database import is_database_healthy


app = FastAPI(title="OpsReplay API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/db-health")
def db_health() -> dict[str, str]:
    if not is_database_healthy():
        raise HTTPException(status_code=503, detail="Database unavailable")

    return {"status": "ok"}
