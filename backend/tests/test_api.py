from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import Settings
from app.main import create_app
from app.models.domain import (
    Ingredient,
    IngredientVisionResult,
    Recipe,
    RecipeIngredientDraft,
    ScoreBreakdown,
)
from app.repositories.sessions import InMemorySessionRepository


def make_png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (1, 1), color=(220, 80, 60)).save(buffer, format="PNG")
    return buffer.getvalue()


PNG_1X1 = make_png()


class FakeAgent:
    async def analyze_image(self, data: bytes, mime_type: str, note: str = ""):
        assert data
        assert mime_type == "image/png"
        return IngredientVisionResult(
            ingredients=[
                Ingredient(name="番茄", normalized_name="番茄", amount="2 个", confidence=0.96)
            ],
            notes="图片清晰",
        )

    async def recommend(self, ingredients, preferences):
        return [
            Recipe(
                title="番茄汤",
                summary="清爽快手",
                servings=preferences.people,
                total_minutes=20,
                difficulty="简单",
                ingredients=[RecipeIngredientDraft(name="番茄", amount="2 个")],
                missing_ingredients=[],
                steps=["切块", "煮汤"],
                nutrition_summary="以蔬菜为主。",
                tags=["快手"],
                score=92,
                score_breakdown=ScoreBreakdown(
                    ingredient_coverage=35,
                    preference_fit=25,
                    nutrition_balance=15,
                    effort_fit=15,
                    provenance=2,
                ),
                score_reasons=["食材覆盖高", "20 分钟完成"],
            )
        ], False

    async def chat(self, session, user_message: str):
        assert session.recipes
        return "可以用少量白醋提味。"


def make_client() -> TestClient:
    settings = Settings(
        DASHSCOPE_API_KEY="test-key",
        MODEL_BASE_URL="https://example.com/v1",
        TAVILY_API_KEY="test-tavily",
    )
    return TestClient(
        create_app(
            settings=settings,
            agent=FakeAgent(),  # type: ignore[arg-type]
            sessions=InMemorySessionRepository(),
        )
    )


def test_full_api_flow() -> None:
    client = make_client()
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["model_configured"] is True

    analysis = client.post(
        "/api/ingredients/analyze",
        files={"image": ("food.png", PNG_1X1, "image/png")},
        data={"note": "桌上的是番茄"},
    )
    assert analysis.status_code == 200
    analysis_body = analysis.json()
    session_id = analysis_body["session_id"]
    assert analysis_body["ingredients"][0]["name"] == "番茄"

    recommendation = client.post(
        "/api/recipes/recommend",
        json={
            "session_id": session_id,
            "ingredients": analysis_body["ingredients"],
            "preferences": {
                "people": 2,
                "flavors": ["清淡"],
                "allergies": [],
                "dislikes": [],
                "max_minutes": 30,
                "difficulty": "简单",
            },
        },
    )
    assert recommendation.status_code == 200
    assert recommendation.json()["recipes"][0]["title"] == "番茄汤"

    chat = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "没有料酒怎么办？"},
    )
    assert chat.status_code == 200
    assert "白醋" in chat.json()["answer"]

    snapshot = client.get(f"/api/sessions/{session_id}")
    assert snapshot.status_code == 200
    assert len(snapshot.json()["messages"]) == 2


def test_invalid_image_returns_structured_error() -> None:
    client = make_client()
    response = client.post(
        "/api/ingredients/analyze",
        files={"image": ("bad.txt", b"not-image", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "unsupported_image"

