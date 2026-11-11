export type Difficulty = "简单" | "适中" | "进阶";

export interface Ingredient {
  name: string;
  normalized_name: string;
  amount: string;
  confidence: number;
  source: "image" | "user";
}

export interface UserPreferences {
  people: number;
  flavors: string[];
  allergies: string[];
  dislikes: string[];
  max_minutes: number;
  difficulty: Difficulty;
}

export interface RecipeIngredient {
  name: string;
  amount: string;
}

export interface RecipeSource {
  title: string;
  url: string;
}

export interface ScoreBreakdown {
  ingredient_coverage: number;
  preference_fit: number;
  nutrition_balance: number;
  effort_fit: number;
  provenance: number;
}

export interface Recipe {
  id: string;
  title: string;
  summary: string;
  servings: number;
  total_minutes: number;
  difficulty: Difficulty;
  ingredients: RecipeIngredient[];
  missing_ingredients: string[];
  steps: string[];
  nutrition_summary: string;
  tags: string[];
  score: number;
  score_breakdown: ScoreBreakdown;
  score_reasons: string[];
  sources: RecipeSource[];
  source_type: "ai" | "ai_with_web";
}

export interface Health {
  status: "ok";
  model: string;
  model_configured: boolean;
  tavily_configured: boolean;
}

export interface AnalyzeResponse {
  session_id: string;
  ingredients: Ingredient[];
  uncertain_items: string[];
  notes: string;
}

export interface RecommendationResponse {
  session_id: string;
  recipes: Recipe[];
  search_used: boolean;
  notice: string;
}

