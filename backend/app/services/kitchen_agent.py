from __future__ import annotations

import base64
import json
from collections.abc import Iterable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.core.errors import AppError
from app.models.domain import (
    Ingredient,
    IngredientVisionResult,
    Recipe,
    RecipeBatch,
    RecipeSource,
    SearchResult,
    SessionState,
    UserPreferences,
)
from app.services.scoring import RecipeScorer


VISION_SYSTEM_PROMPT = """你是严谨的食材识别助手。只识别图片中可见或高度可信的可食用食材，
不要把餐具、包装文字或背景物体当作食材。数量不确定时用“约”或“适量”，低置信项目放入 uncertain_items。
输出简体中文，normalized_name 使用常见中文食材名。"""

RECIPE_SYSTEM_PROMPT = """你是专业但务实的中式私厨管家。根据已确认食材、偏好与可选网络摘要生成菜谱。
硬性规则：过敏原绝对禁止；不要声称精确医学营养数值；缺少食材必须明确列出；步骤要可执行；
search_source_urls 只能使用提供的 URL，不得编造。nutrition_groups 从“蛋白质、蔬菜、水果、主食、奶类”中选择实际覆盖项。
输出简体中文。"""

CHAT_SYSTEM_PROMPT = """你是“灶边 AI”私厨管家。回答必须基于当前会话食材和菜谱，简洁、具体、可操作。
过敏原优先于一切建议。聊天仅提供建议，不声称已经修改菜谱卡片；若用户要求修改，说明可如何调整并提醒重新生成。
营养信息仅作一般参考。"""


class KitchenAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.scorer = RecipeScorer()
        self._llm = self._build_llm()
        self._search = self._build_search_tool()

    def _build_llm(self) -> ChatOpenAI | None:
        if not self.settings.model_ready:
            return None
        return ChatOpenAI(
            model=self.settings.model_name,
            api_key=self.settings.dashscope_api_key,
            base_url=self.settings.model_base_url,
            temperature=0.2,
            timeout=90,
            max_retries=1,
        )

    def _build_search_tool(self):
        if not self.settings.tavily_ready:
            return None
        try:
            from langchain_tavily import TavilySearch

            return TavilySearch(
                api_key=self.settings.tavily_api_key.get_secret_value(),
                max_results=5,
                topic="general",
                include_raw_content=False,
            )
        except Exception:
            return None

    def _require_llm(self) -> ChatOpenAI:
        if not self._llm:
            raise AppError(
                "model_not_configured",
                "模型 API 尚未配置，请检查项目根目录的 .env。",
                status_code=503,
            )
        return self._llm

    async def analyze_image(self, data: bytes, mime_type: str, note: str = "") -> IngredientVisionResult:
        llm = self._require_llm()
        encoded = base64.b64encode(data).decode("ascii")
        prompt = "请识别这张厨房或冰箱照片中的食材。"
        if note.strip():
            prompt += f" 用户补充：{note.strip()}"
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
            ]
        )
        try:
            chain = llm.with_structured_output(IngredientVisionResult, method="function_calling")
            result = await chain.ainvoke([SystemMessage(content=VISION_SYSTEM_PROMPT), message])
            return IngredientVisionResult.model_validate(result)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                "vision_failed",
                "食材识别暂时失败，请稍后重试或换一张更清晰的图片。",
                status_code=502,
                retryable=True,
            ) from exc

    async def _search_recipes(
        self, ingredients: list[Ingredient], preferences: UserPreferences
    ) -> list[SearchResult]:
        if not self._search:
            return []
        names = " ".join(item.normalized_name or item.name for item in ingredients[:10])
        flavors = " ".join(preferences.flavors)
        query = f"{names} {flavors} 家常菜 菜谱 做法 {preferences.max_minutes}分钟"
        try:
            raw = await self._search.ainvoke({"query": query})
        except Exception:
            return []

        if isinstance(raw, dict):
            items = raw.get("results", [])
        elif isinstance(raw, list):
            items = raw
        else:
            return []
        results: list[SearchResult] = []
        for item in items[:5]:
            if not isinstance(item, dict) or not item.get("url"):
                continue
            results.append(
                SearchResult(
                    title=str(item.get("title") or "菜谱参考"),
                    url=str(item["url"]),
                    content=str(item.get("content") or item.get("snippet") or "")[:1200],
                )
            )
        return results

    @staticmethod
    def _source_map(results: Iterable[SearchResult]) -> dict[str, RecipeSource]:
        mapped: dict[str, RecipeSource] = {}
        for result in results:
            try:
                mapped[result.url] = RecipeSource(title=result.title, url=result.url)
            except ValueError:
                continue
        return mapped

    async def recommend(
        self,
        ingredients: list[Ingredient],
        preferences: UserPreferences,
    ) -> tuple[list[Recipe], bool]:
        llm = self._require_llm()
        search_results = await self._search_recipes(ingredients, preferences)
        source_map = self._source_map(search_results)
        payload = {
            "confirmed_ingredients": [item.model_dump() for item in ingredients],
            "preferences": preferences.model_dump(),
            "recipe_count": self.settings.recipe_count,
            "web_references": [item.model_dump() for item in search_results],
        }
        message = HumanMessage(
            content="请生成并排序前的候选菜谱。输入数据：\n"
            + json.dumps(payload, ensure_ascii=False, indent=2)
        )
        try:
            chain = llm.with_structured_output(RecipeBatch, method="function_calling")
            batch = RecipeBatch.model_validate(
                await chain.ainvoke([SystemMessage(content=RECIPE_SYSTEM_PROMPT), message])
            )
        except Exception as exc:
            raise AppError(
                "recommendation_failed",
                "菜谱生成暂时失败，请稍后重试。",
                status_code=502,
                retryable=True,
            ) from exc

        recipes: list[Recipe] = []
        for draft in batch.recipes:
            if self.scorer.contains_allergen(draft, preferences.allergies):
                continue
            sources = [source_map[url] for url in draft.search_source_urls if url in source_map]
            recipes.append(self.scorer.score(draft, ingredients, preferences, sources))
        recipes.sort(key=lambda recipe: recipe.score, reverse=True)
        if not recipes:
            raise AppError(
                "no_safe_recipe",
                "没有生成符合过敏原限制的菜谱，请调整食材或偏好后重试。",
                status_code=422,
            )
        return recipes, any(recipe.sources for recipe in recipes)

    async def chat(self, session: SessionState, user_message: str) -> str:
        llm = self._require_llm()
        context = {
            "ingredients": [item.model_dump() for item in session.ingredients],
            "preferences": session.preferences.model_dump() if session.preferences else None,
            "recipes": [
                {
                    "title": recipe.title,
                    "ingredients": [item.model_dump() for item in recipe.ingredients],
                    "steps": recipe.steps,
                    "allergies": session.preferences.allergies if session.preferences else [],
                }
                for recipe in session.recipes[:4]
            ],
        }
        messages = [
            SystemMessage(content=CHAT_SYSTEM_PROMPT + "\n当前会话：" + json.dumps(context, ensure_ascii=False))
        ]
        for item in session.messages[-8:]:
            if item.role == "user":
                messages.append(HumanMessage(content=item.content))
            else:
                messages.append(AIMessage(content=item.content))
        messages.append(HumanMessage(content=user_message))
        try:
            result = await llm.ainvoke(messages)
            if isinstance(result.content, str):
                return result.content.strip()
            return "".join(str(part) for part in result.content).strip()
        except Exception as exc:
            raise AppError(
                "chat_failed",
                "私厨管家暂时无法回答，请稍后重试。",
                status_code=502,
                retryable=True,
            ) from exc

