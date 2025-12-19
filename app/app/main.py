from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api import router
from app.config.base_config import settings
from app.utils.logger import log
from app.config.database_config import init_db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    await init_db()
    log.info(f"{settings.APP_NAME} v{settings.APP_VERSION} Starting up...")
    log.info(f"website: http://{settings.HOST}:{settings.PORT}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    log.info(f"{settings.APP_NAME} v{settings.APP_VERSION} Shutting down...")


@app.get("/", tags=["root"])
async def root():
    return {
        "message": f"{settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "website": f"https://{settings.HOST}:{settings.PORT}/docs",
        "api": f"https://{settings.HOST}:{settings.PORT}/api"
    }