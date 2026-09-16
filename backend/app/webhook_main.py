from fastapi import FastAPI

from app.routers.github_webhook import router as github_webhook_router


app = FastAPI(
    title="OpsReplay GitHub Webhook Ingress",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(github_webhook_router)
