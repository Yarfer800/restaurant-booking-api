from fastapi import APIRouter

from api.v1 import auth

api_router = APIRouter()
api_router.include_router(auth.router)