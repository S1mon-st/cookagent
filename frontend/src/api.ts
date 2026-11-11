import type {
  AnalyzeResponse,
  Health,
  Ingredient,
  RecommendationResponse,
  UserPreferences,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  readonly retryable: boolean;

  constructor(message: string, retryable = false) {
    super(message);
    this.retryable = retryable;
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    return response.json() as Promise<T>;
  }
  let payload: { message?: string; retryable?: boolean } = {};
  try {
    payload = await response.json();
  } catch {
    // 保留通用错误信息
  }
  throw new ApiError(payload.message ?? "请求失败，请稍后重试。", payload.retryable ?? false);
}

export async function getHealth(): Promise<Health> {
  return parseResponse(await fetch(`${API_BASE}/health`));
}

export async function analyzeImage(file: File, note: string): Promise<AnalyzeResponse> {
  const body = new FormData();
  body.append("image", file);
  body.append("note", note);
  return parseResponse(
    await fetch(`${API_BASE}/ingredients/analyze`, {
      method: "POST",
      body,
    }),
  );
}

export async function recommendRecipes(
  sessionId: string,
  ingredients: Ingredient[],
  preferences: UserPreferences,
): Promise<RecommendationResponse> {
  return parseResponse(
    await fetch(`${API_BASE}/recipes/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, ingredients, preferences }),
    }),
  );
}

export async function sendChat(sessionId: string, message: string): Promise<string> {
  const payload = await parseResponse<{ answer: string }>(
    await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    }),
  );
  return payload.answer;
}

