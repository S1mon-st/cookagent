from __future__ import annotations

from app.models.domain import (
    Ingredient,
    Recipe,
    RecipeDraft,
    RecipeSource,
    ScoreBreakdown,
    UserPreferences,
)


class RecipeScorer:
    _difficulty_order = {"简单": 1, "适中": 2, "进阶": 3}

    @staticmethod
    def _contains(text: str, terms: list[str]) -> bool:
        lowered = text.casefold()
        return any(term.strip().casefold() in lowered for term in terms if term.strip())

    def score(
        self,
        draft: RecipeDraft,
        available: list[Ingredient],
        preferences: UserPreferences,
        sources: list[RecipeSource],
    ) -> Recipe:
        available_names = [item.normalized_name or item.name for item in available]
        required_names = [item.name for item in draft.ingredients]
        covered = sum(1 for name in required_names if self._contains(name, available_names))
        coverage_ratio = covered / max(len(required_names), 1)
        ingredient_coverage = round(35 * coverage_ratio, 1)

        recipe_text = " ".join(required_names + draft.tags + [draft.title])
        preference_fit = 25.0 if not self._contains(recipe_text, preferences.dislikes) else 8.0

        groups = {group.strip() for group in draft.nutrition_groups if group.strip()}
        nutrition_balance = round(min(len(groups), 4) / 4 * 20, 1)

        time_points = 10.0 if draft.total_minutes <= preferences.max_minutes else max(
            0.0, 10 - (draft.total_minutes - preferences.max_minutes) / 6
        )
        desired = self._difficulty_order[preferences.difficulty]
        actual = self._difficulty_order[draft.difficulty]
        difficulty_points = max(0.0, 5.0 - abs(desired - actual) * 2.5)
        effort_fit = round(time_points + difficulty_points, 1)

        provenance = 5.0 if sources else 2.0
        breakdown = ScoreBreakdown(
            ingredient_coverage=ingredient_coverage,
            preference_fit=preference_fit,
            nutrition_balance=nutrition_balance,
            effort_fit=effort_fit,
            provenance=provenance,
        )
        total = round(sum(breakdown.model_dump().values()), 1)

        reasons = [f"现有食材覆盖约 {round(coverage_ratio * 100)}%"]
        if draft.total_minutes <= preferences.max_minutes:
            reasons.append(f"可在 {draft.total_minutes} 分钟左右完成")
        elif sources:
            reasons.append("包含可追溯的网络参考")
        else:
            reasons.append(f"难度为{draft.difficulty}")

        return Recipe(
            **draft.model_dump(exclude={"nutrition_groups", "search_source_urls"}),
            score=total,
            score_breakdown=breakdown,
            score_reasons=reasons[:2],
            sources=sources,
            source_type="ai_with_web" if sources else "ai",
        )

    def contains_allergen(self, draft: RecipeDraft, allergies: list[str]) -> bool:
        if not allergies:
            return False
        text = " ".join(
            [draft.title, draft.summary, *draft.missing_ingredients]
            + [ingredient.name for ingredient in draft.ingredients]
        )
        return self._contains(text, allergies)

