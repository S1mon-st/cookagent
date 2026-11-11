import type { Recipe } from "../types";

export type SortMode = "score" | "fast" | "easy" | "coverage";

const difficultyRank = { 简单: 1, 适中: 2, 进阶: 3 } as const;

export function sortRecipes(recipes: Recipe[], mode: SortMode): Recipe[] {
  return [...recipes].sort((a, b) => {
    if (mode === "fast") return a.total_minutes - b.total_minutes;
    if (mode === "easy") return difficultyRank[a.difficulty] - difficultyRank[b.difficulty];
    if (mode === "coverage") {
      return b.score_breakdown.ingredient_coverage - a.score_breakdown.ingredient_coverage;
    }
    return b.score - a.score;
  });
}

