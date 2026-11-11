from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from time import perf_counter

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from langchain_core.messages import HumanMessage

from app.core.config import get_settings
from app.models.domain import Ingredient, UserPreferences
from app.services.kitchen_agent import KitchenAgent


async def main() -> None:
    settings = get_settings()
    agent = KitchenAgent(settings)
    report: dict[str, object] = {
        "model": settings.model_name,
        "model_configured": settings.model_ready,
        "tavily_configured": settings.tavily_ready,
        "model_ok": False,
        "tavily_ok": False,
    }

    if agent._llm is not None:
        started = perf_counter()
        try:
            response = await agent._llm.ainvoke([HumanMessage(content="只回答：OK")])
            report["model_ok"] = bool(response.content)
            report["model_ms"] = round((perf_counter() - started) * 1000)
        except Exception as exc:
            report["model_error_type"] = type(exc).__name__

    if agent._search is not None:
        started = perf_counter()
        try:
            result = await agent._search.ainvoke({"query": "番茄炒蛋 家常菜谱"})
            items = result.get("results", []) if isinstance(result, dict) else result
            report["tavily_ok"] = bool(items)
            report["tavily_result_count"] = len(items) if isinstance(items, list) else 0
            report["tavily_ms"] = round((perf_counter() - started) * 1000)
        except Exception as exc:
            report["tavily_error_type"] = type(exc).__name__

    image_args = [argument for argument in sys.argv[1:] if not argument.startswith("--")]
    if image_args:
        image_path = Path(image_args[0]).resolve()
        mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
        started = perf_counter()
        try:
            vision = await agent.analyze_image(
                image_path.read_bytes(),
                mime_types.get(image_path.suffix.lower(), "image/png"),
                "这是连通性验证；请严格按图片内容识别，没有食材就返回空列表。",
            )
            report["vision_structured_ok"] = isinstance(vision.ingredients, list)
            report["vision_ingredient_count"] = len(vision.ingredients)
            report["vision_ms"] = round((perf_counter() - started) * 1000)
        except Exception as exc:
            report["vision_structured_ok"] = False
            report["vision_error_type"] = type(exc).__name__

    if "--recommend" in sys.argv:
        started = perf_counter()
        try:
            recipes, search_used = await agent.recommend(
                [
                    Ingredient(name="番茄", normalized_name="番茄", amount="2个", confidence=1, source="user"),
                    Ingredient(name="鸡蛋", normalized_name="鸡蛋", amount="3个", confidence=1, source="user"),
                ],
                UserPreferences(
                    people=2,
                    flavors=["家常"],
                    allergies=["花生"],
                    dislikes=[],
                    max_minutes=35,
                    difficulty="简单",
                ),
            )
            report["recommendation_ok"] = len(recipes) >= 1
            report["recipe_count"] = len(recipes)
            report["search_used_in_recipe"] = search_used
            report["source_count"] = sum(len(recipe.sources) for recipe in recipes)
            report["scores_valid"] = all(0 <= recipe.score <= 100 for recipe in recipes)
            report["recommendation_ms"] = round((perf_counter() - started) * 1000)
        except Exception as exc:
            report["recommendation_ok"] = False
            report["recommendation_error_type"] = type(exc).__name__

    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
