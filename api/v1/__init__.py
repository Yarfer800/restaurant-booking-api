from fastapi import APIRouter

from api.v1 import auth, reservations, restaurants, tables

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(restaurants.router)
api_router.include_router(tables.router)
api_router.include_router(reservations.router)
