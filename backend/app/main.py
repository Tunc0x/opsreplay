from fastapi import FastAPI


app = FastAPI(title="OpsReplay API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
