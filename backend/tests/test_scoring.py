from app.models.domain import (
    Ingredient,
    RecipeDraft,
    RecipeIngredientDraft,
    UserPreferences,
)
from app.services.scoring import RecipeScorer


def make_draft(**overrides) -> RecipeDraft:
    payload = {
        "title": "番茄鸡蛋面",
        "summary": "快手家常面",
        "servings": 2,
        "total_minutes": 20,
        "difficulty": "简单",
        "ingredients": [
            RecipeIngredientDraft(name="番茄", amount="2 个"),
            RecipeIngredientDraft(name="鸡蛋", amount="2 个"),
            RecipeIngredientDraft(name="面条", amount="200 克"),
        ],
        "missing_ingredients": ["面条"],
        "steps": ["炒番茄鸡蛋", "煮面并组合"],
        "nutrition_summary": "包含蛋白质、蔬菜和主食。",
        "nutrition_groups": ["蛋白质", "蔬菜", "主食"],
        "tags": ["家常", "快手"],
        "search_source_urls": [],
    }
    payload.update(overrides)
    return RecipeDraft.model_validate(payload)


def test_score_rewards_coverage_and_time_fit() -> None:
    scorer = RecipeScorer()
    recipe = scorer.score(
        make_draft(),
        [
            Ingredient(name="番茄", normalized_name="番茄"),
            Ingredient(name="鸡蛋", normalized_name="鸡蛋"),
        ],
        UserPreferences(max_minutes=30, difficulty="简单"),
        [],
    )

    assert recipe.score_breakdown.ingredient_coverage > 20
    assert recipe.score_breakdown.effort_fit == 15
    assert recipe.score <= 100
    assert "现有食材覆盖" in recipe.score_reasons[0]


def test_allergen_is_absolute_filter() -> None:
    scorer = RecipeScorer()
    assert scorer.contains_allergen(make_draft(), ["鸡蛋"])
    assert not scorer.contains_allergen(make_draft(), ["花生"])

