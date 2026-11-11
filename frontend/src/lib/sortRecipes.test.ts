import { describe, expect, it } from "vitest";

import type { Recipe } from "../types";
import { sortRecipes } from "./sortRecipes";

const base = {
  summary: "summary",
  servings: 2,
  difficulty: "适中" as const,
  ingredients: [],
  missing_ingredients: [],
  steps: ["step"],
  nutrition_summary: "balanced",
  tags: [],
  score_reasons: [],
  sources: [],
  source_type: "ai" as const,
};

const recipes: Recipe[] = [
  { ...base, id: "slow", title: "慢菜", total_minutes: 60, score: 95, score_breakdown: { ingredient_coverage: 20, preference_fit: 25, nutrition_balance: 20, effort_fit: 15, provenance: 5 } },
  { ...base, id: "fast", title: "快菜", total_minutes: 15, score: 82, score_breakdown: { ingredient_coverage: 35, preference_fit: 25, nutrition_balance: 15, effort_fit: 5, provenance: 2 } },
];

describe("sortRecipes", () => {
  it("按综合分从高到低排序", () => {
    expect(sortRecipes(recipes, "score")[0].id).toBe("slow");
  });

  it("按用时从短到长排序", () => {
    expect(sortRecipes(recipes, "fast")[0].id).toBe("fast");
  });

  it("按食材覆盖率排序且不修改原数组", () => {
    expect(sortRecipes(recipes, "coverage")[0].id).toBe("fast");
    expect(recipes[0].id).toBe("slow");
  });
});

