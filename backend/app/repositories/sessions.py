from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock

from app.models.domain import (
    ConversationMessage,
    IngredientVisionResult,
    Recipe,
    SessionState,
    UserPreferences,
)


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = RLock()

    def create(self, analysis: IngredientVisionResult) -> SessionState:
        session = SessionState(
            ingredients=analysis.ingredients,
            uncertain_items=analysis.uncertain_items,
            analysis_notes=analysis.notes,
        )
        with self._lock:
            self._sessions[session.id] = session
        return session.model_copy(deep=True)

    def get(self, session_id: str) -> SessionState | None:
        with self._lock:
            session = self._sessions.get(session_id)
            return session.model_copy(deep=True) if session else None

    def set_recipes(
        self,
        session_id: str,
        ingredients: list,
        preferences: UserPreferences,
        recipes: list[Recipe],
    ) -> SessionState | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            session.ingredients = ingredients
            session.preferences = preferences
            session.recipes = recipes
            session.updated_at = datetime.now(timezone.utc)
            return session.model_copy(deep=True)

    def add_message(self, session_id: str, message: ConversationMessage) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            session.messages.append(message)
            session.messages = session.messages[-20:]
            session.updated_at = datetime.now(timezone.utc)
            return True

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

