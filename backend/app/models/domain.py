from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


Difficulty = Literal["简单", "适中", "进阶"]


class Ingredient(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    normalized_name: str = Field(default="", max_length=40)
    amount: str = Field(default="适量", max_length=40)
    confidence: float = Field(default=1.0, ge=0, le=1)
    source: Literal["image", "user"] = "image"

    @field_validator("name", "normalized_name", "amount", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class IngredientVisionResult(BaseModel):
    ingredients: list[Ingredient] = Field(default_factory=list, max_length=50)
    uncertain_items: list[str] = Field(default_factory=list, max_length=12)
    notes: str = Field(default="", max_length=300)


class UserPreferences(BaseModel):
    people: int = Field(default=2, ge=1, le=12)
    flavors: list[str] = Field(default_factory=list, max_length=8)
    allergies: list[str] = Field(default_factory=list, max_length=12)
    dislikes: list[str] = Field(default_factory=list, max_length=12)
    max_minutes: int = Field(default=45, ge=10, le=240)
    difficulty: Difficulty = "适中"


class RecipeIngredientDraft(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    amount: str = Field(default="适量", max_length=50)


class RecipeDraft(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=240)
    servings: int = Field(ge=1, le=12)
    total_minutes: int = Field(ge=5, le=480)
    difficulty: Difficulty
    ingredients: list[RecipeIngredientDraft] = Field(min_length=1, max_length=30)
    missing_ingredients: list[str] = Field(default_factory=list, max_length=15)
    steps: list[str] = Field(min_length=1, max_length=20)
    nutrition_summary: str = Field(min_length=1, max_length=300)
    nutrition_groups: list[str] = Field(default_factory=list, max_length=8)
    tags: list[str] = Field(default_factory=list, max_length=10)
    search_source_urls: list[str] = Field(default_factory=list, max_length=6)


class RecipeBatch(BaseModel):
    recipes: list[RecipeDraft] = Field(min_length=1, max_length=8)


class RecipeSource(BaseModel):
    title: str
    url: HttpUrl


class ScoreBreakdown(BaseModel):
    ingredient_coverage: float = Field(ge=0, le=35)
    preference_fit: float = Field(ge=0, le=25)
    nutrition_balance: float = Field(ge=0, le=20)
    effort_fit: float = Field(ge=0, le=15)
    provenance: float = Field(ge=0, le=5)


class Recipe(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    summary: str
    servings: int
    total_minutes: int
    difficulty: Difficulty
    ingredients: list[RecipeIngredientDraft]
    missing_ingredients: list[str]
    steps: list[str]
    nutrition_summary: str
    tags: list[str]
    score: float = Field(ge=0, le=100)
    score_breakdown: ScoreBreakdown
    score_reasons: list[str]
    sources: list[RecipeSource] = Field(default_factory=list)
    source_type: Literal["ai", "ai_with_web"] = "ai"


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionState(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    ingredients: list[Ingredient] = Field(default_factory=list)
    analysis_notes: str = ""
    uncertain_items: list[str] = Field(default_factory=list)
    preferences: UserPreferences | None = None
    recipes: list[Recipe] = Field(default_factory=list)
    messages: list[ConversationMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SearchResult(BaseModel):
    title: str
    url: str
    content: str = ""


class RecommendationRequest(BaseModel):
    session_id: str
    ingredients: list[Ingredient] = Field(min_length=1, max_length=50)
    preferences: UserPreferences


class RecommendationResponse(BaseModel):
    session_id: str
    recipes: list[Recipe]
    search_used: bool
    notice: str


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=1500)


class ChatResponse(BaseModel):
    session_id: str
    answer: str


class AnalyzeResponse(BaseModel):
    session_id: str
    ingredients: list[Ingredient]
    uncertain_items: list[str]
    notes: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    model: str
    model_configured: bool
    tavily_configured: bool


class ErrorResponse(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: dict | None = None

