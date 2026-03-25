import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.logging import configure_logging, get_logger
import features.models_registry  # noqa: F401
from features.auth.wiring import include_auth_routers
from features.deliveries.wiring import deliveries_router
from features.locations.wiring import locations_router
from features.organizations.wiring import organizations_router
from features.products.wiring import products_router

configure_logging()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="PuntoEntrega API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    include_auth_routers(app)
    app.include_router(organizations_router, tags=["organizations"])
    app.include_router(locations_router, prefix="/locations", tags=["locations"])
    app.include_router(products_router, prefix="/products", tags=["products"])
    app.include_router(deliveries_router, prefix="/deliveries", tags=["deliveries"])

    if settings.LOG_REQUESTS:
        @app.middleware("http")
        async def request_logging_middleware(request: Request, call_next):
            started = time.perf_counter()
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - started) * 1000
            forwarded_for = request.headers.get("x-forwarded-for", "")
            client_ip = (
                forwarded_for.split(",")[0].strip()
                if forwarded_for
                else (request.client.host if request.client else "unknown")
            )
            user_agent = request.headers.get("user-agent", "unknown")
            path = request.url.path

            logger.info(
                "%s %s -> %s (%.2fms) ip=%s ua=%s",
                request.method,
                path,
                response.status_code,
                elapsed_ms,
                client_ip,
                user_agent,
            )

            if path == "/auth/jwt/login":
                level = logger.info if response.status_code < 400 else logger.warning
                level(
                    "Auth login attempt result=%s status=%s ip=%s ua=%s",
                    "success" if response.status_code < 400 else "failure",
                    response.status_code,
                    client_ip,
                    user_agent,
                )

            return response

    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint for Docker/orchestrator probes."""
        return {"status": "healthy"}

    return app


app = create_app()
