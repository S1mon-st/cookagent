from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.repositories.sessions import InMemorySessionRepository
from app.services.kitchen_agent import KitchenAgent


logger = logging.getLogger("cookagent")


def create_app(
    *,
    settings: Settings | None = None,
    agent: KitchenAgent | None = None,
    sessions: InMemorySessionRepository | None = None,
) -> FastAPI:
    current_settings = settings or get_settings()
    app = FastAPI(
        title=current_settings.app_name,
        version="0.1.0",
        description="上传食材图片，获得可解释的私厨菜谱推荐。",
    )
    app.state.settings = current_settings
    app.state.agent = agent or KitchenAgent(current_settings)
    app.state.sessions = sessions or InMemorySessionRepository()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=current_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "retryable": exc.retryable,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled request error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "code": "internal_error",
                "message": "服务暂时出现问题，请稍后重试。",
                "retryable": True,
                "details": None,
            },
        )

    app.include_router(router)
    return app


app = create_app()

