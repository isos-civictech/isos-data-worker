from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine

from src.config import Settings


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_engine(request: Request) -> AsyncEngine:
    return request.app.state.engine
