from fastapi import APIRouter

from api.v1 import auth, restaurants

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(restaurants.router)