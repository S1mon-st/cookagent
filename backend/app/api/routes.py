from __future__ import annotations

from fastapi import APIRouter, File, Form, Request, UploadFile

from app.core.errors import AppError
from app.models.domain import (
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    ConversationMessage,
    HealthResponse,
    RecommendationRequest,
    RecommendationResponse,
    SessionState,
)
from app.services.image_validation import validate_image


router = APIRouter(prefix="/api")


def _services(request: Request):
    return request.app.state.settings, request.app.state.agent, request.app.state.sessions


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings, _, _ = _services(request)
    return HealthResponse(
        model=settings.model_name,
        model_configured=settings.model_ready,
        tavily_configured=settings.tavily_ready,
    )


@router.post("/ingredients/analyze", response_model=AnalyzeResponse)
async def analyze_ingredients(
    request: Request,
    image: UploadFile = File(...),
    note: str = Form(default="", max_length=500),
) -> AnalyzeResponse:
    settings, agent, sessions = _services(request)
    data = await image.read(settings.max_image_mb * 1024 * 1024 + 1)
    mime_type = validate_image(data, image.content_type, settings.max_image_mb * 1024 * 1024)
    analysis = await agent.analyze_image(data, mime_type, note)
    session = sessions.create(analysis)
    return AnalyzeResponse(
        session_id=session.id,
        ingredients=session.ingredients,
        uncertain_items=session.uncertain_items,
        notes=session.analysis_notes,
    )


@router.post("/recipes/recommend", response_model=RecommendationResponse)
async def recommend_recipes(
    payload: RecommendationRequest, request: Request
) -> RecommendationResponse:
    _, agent, sessions = _services(request)
    if not sessions.get(payload.session_id):
        raise AppError("session_not_found", "当前会话已失效，请重新识别图片。", status_code=404)
    recipes, search_used = await agent.recommend(payload.ingredients, payload.preferences)
    sessions.set_recipes(payload.session_id, payload.ingredients, payload.preferences, recipes)
    notice = (
        "已结合网络资料生成，烹饪前请核对来源与过敏原。"
        if search_used
        else "当前建议由 AI 生成，烹饪前请核对食材与过敏原。"
    )
    return RecommendationResponse(
        session_id=payload.session_id,
        recipes=recipes,
        search_used=search_used,
        notice=notice,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    _, agent, sessions = _services(request)
    session = sessions.get(payload.session_id)
    if not session:
        raise AppError("session_not_found", "当前会话已失效，请重新识别图片。", status_code=404)
    answer = await agent.chat(session, payload.message)
    sessions.add_message(payload.session_id, ConversationMessage(role="user", content=payload.message))
    sessions.add_message(payload.session_id, ConversationMessage(role="assistant", content=answer))
    return ChatResponse(session_id=payload.session_id, answer=answer)


@router.get("/sessions/{session_id}", response_model=SessionState)
async def get_session(session_id: str, request: Request) -> SessionState:
    _, _, sessions = _services(request)
    session = sessions.get(session_id)
    if not session:
        raise AppError("session_not_found", "没有找到该会话。", status_code=404)
    return session


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, request: Request) -> None:
    _, _, sessions = _services(request)
    sessions.delete(session_id)

