from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()
# Keep the API metadata and interactive documentation paths in one place.
app = FastAPI(
    title=settings.app_name,
    description="API de atendimento ao cliente com IA, memória de conversa e transferência para atendimento humano.",
    version="1.0.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
)
# Mount the customer-service endpoints using the configured optional route prefix.
app.include_router(router, prefix=settings.api_v1_prefix)