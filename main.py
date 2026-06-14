import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import config

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=config.app_name,
        description='REST API для бронирования столов в ресторанах.',
        version='0.1.0',
        lifespan=lifespan,
    )

    @app.get('/health', tags=['health'], summary='Проверка работоспособности')
    async def health() -> dict[str, str]:
        return {'status': 'ok'}

    return app


app = create_app()