import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.v1 import api_router
from config import config
from core.db import session_manager
from core.exceptions import register_exception_handlers
from core.redis import redis_service

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    session_manager.init()
    await redis_service.connect()
    yield
    await redis_service.close()
    await session_manager.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title=config.app_name,
        description='REST API для бронирования столов в ресторанах.',
        version='0.1.0',
        lifespan=lifespan,
    )
    app.include_router(api_router)
    register_exception_handlers(app)

    @app.get('/health', tags=['health'], summary='Проверка работоспособности')
    async def health() -> dict[str, str]:
        return {'status': 'ok'}

    return app


app = create_app()