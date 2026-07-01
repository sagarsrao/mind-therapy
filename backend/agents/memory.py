import os
import json
from datetime import datetime
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

class EntryAnalysis(BaseModel):
    mood_score: int = Field(
        description="Estimated mood score from 1 (extremely distressed/depressed) to 10 (extremely happy/peaceful)."
    )
    themes: list[str] = Field(
        description="Key themes or topics mentioned (e.g., 'work stress', 'loneliness', 'relationship conflict', 'gratitude')."
    )
    summary: str = Field(
        description="A 1-sentence summary of the user's entry."
    )

class HistoryTrend(BaseModel):
    trend: str = Field(
        description="The mood trend. Must be 'stable', 'improving', or 'declining'."
    )
    reason: str = Field(
        description="Brief explanation of the trend analysis."
    )
    recurring_themes: list[str] = Field(
        description="Themes that have appeared repeatedly in recent entries."
    )

class MemoryAgent:
    def __init__(self, data_dir: str = "backend/data", model_name: str = "gemini-2.5-flash"):
        self.data_dir = data_dir
        self.model_name = model_name
        os.makedirs(data_dir, exist_ok=True)
        self.client = genai.Client()

    def _get_history_file(self, user_id: str) -> str:
        # Avoid path traversal by cleaning the user_id
        safe_user_id = "".join([c for c in user_id if c.isalnum() or c in ("-", "_")])
        return os.path.join(self.data_dir, f"history_{safe_user_id}.json")

    def get_history(self, user_id: str) -> list[dict]:
        file_path = self._get_history_file(user_id)
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading history file: {e}")
            return []

    def get_recent_history(self, user_id: str, limit: int = 5) -> list[dict]:
        history = self.get_history(user_id)
        return history[-limit:]

    def save_history(self, user_id: str, history: list[dict]):
        file_path = self._get_history_file(user_id)
        try:
            with open(file_path, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"Error writing history file: {e}")

    def build_entry(self, text: str, analysis: EntryAnalysis) -> dict:
        """Builds the persisted history record from a completed entry analysis."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "text": text,
            "mood_score": analysis.mood_score,
            "themes": analysis.themes,
            "summary": analysis.summary
        }

    def append_entry_and_analyze_trend(
        self,
        user_id: str,
        entry: dict,
        *,
        allow_llm_trend_check: bool = True,
    ) -> tuple[dict, HistoryTrend]:
        """Persists an already-analyzed entry and evaluates the updated history."""
        history = self.get_history(user_id)
        history.append(entry)
        self.save_history(user_id, history)
        return entry, self.analyze_trend(
            history,
            allow_llm_check=allow_llm_trend_check,
        )

    def analyze_entry(self, text: str) -> EntryAnalysis:
        """Analyze a single entry to extract mood score and themes."""
        prompt = f"""
Analyze the following journal entry. Estimate a mood score from 1 (worst) to 10 (best), extract the key emotional themes, and write a 1-sentence summary.
Use specific themes when the entry contains a clear topic or activity. For example, "I feel good after hitting the gym" should include themes like "exercise" and "positive mood", not just "general".
Only use "general" when no specific topic, activity, or emotion can be inferred.

Journal Entry:
\"\"\"
{text}
\"\"\"
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=EntryAnalysis,
                    temperature=0.1,
                ),
            )
            data = json.loads(response.text)
            return EntryAnalysis(**data)
        except Exception as e:
            print(f"Error analyzing entry: {e}")
            return self._fallback_entry_analysis(text)

    def _fallback_entry_analysis(self, text: str) -> EntryAnalysis:
        lower_text = text.lower()
        themes = []
        mood_score = 5

        def add_theme(theme: str):
            if theme not in themes:
                themes.append(theme)

        positive_terms = ("good", "great", "happy", "happiness", "excited", "proud", "better", "calm", "peaceful", "satisfied")
        distress_terms = ("bad", "sad", "stress", "stressed", "anxious", "overwhelmed", "tired", "exhausted", "lonely")

        if any(term in lower_text for term in positive_terms):
            mood_score = max(mood_score, 8)
            add_theme("positive mood")

        if any(term in lower_text for term in distress_terms):
            mood_score = min(mood_score, 4)
            add_theme("distress")

        if any(term in lower_text for term in ("gym", "workout", "exercise", "run", "walk", "training", "stretch", "stretching", "cool down", "cooldown")):
            add_theme("exercise")
            if mood_score >= 5:
                mood_score = max(mood_score, 8)

        if any(term in lower_text for term in ("strength", "conditioning", "weights", "lifting")):
            add_theme("strength training")
            if mood_score >= 5:
                mood_score = max(mood_score, 8)

        if any(term in lower_text for term in ("work", "office", "job", "deadline", "meeting")):
            add_theme("work")

        if any(term in lower_text for term in ("family", "friend", "partner", "relationship")):
            add_theme("relationships")

        if not themes:
            add_theme("general")

        summary = "The user shared a journal check-in."
        if ("exercise" in themes or "strength training" in themes) and "positive mood" in themes:
            summary = "The user felt good after movement or exercise."
        elif "strength training" in themes:
            summary = "The user mentioned strength and conditioning."
        elif "exercise" in themes:
            summary = "The user mentioned movement or exercise."
        elif "positive mood" in themes:
            summary = "The user shared a positive mood."
        elif "distress" in themes:
            summary = "The user shared difficult feelings."
        elif "work" in themes:
            summary = "The user mentioned work."

        return EntryAnalysis(
            mood_score=mood_score,
            themes=themes,
            summary=summary
        )

    def add_and_analyze_entry(self, user_id: str, text: str) -> tuple[dict, HistoryTrend]:
        """Adds a new entry to history, analyzes it, and evaluates the overall trend."""
        # 1. Analyze the current entry
        analysis = self.analyze_entry(text)

        entry = self.build_entry(text, analysis)
        return self.append_entry_and_analyze_trend(user_id, entry)

    def _calculated_trend(self, scores: list[int], recurring_themes: list[str]) -> HistoryTrend:
        if scores[-1] > scores[0]:
            return HistoryTrend(
                trend="improving",
                reason="Mood has generally improved since the start of the tracked period.",
                recurring_themes=recurring_themes
            )

        return HistoryTrend(
            trend="stable",
            reason="Mood appears stable with normal fluctuations.",
            recurring_themes=recurring_themes
        )

    def _should_run_llm_trend_check(
        self,
        recent: list[dict],
        scores: list[int],
        recurring_themes: list[str],
    ) -> bool:
        """
        Limits slower thematic trend checks to histories where local signals suggest
        the extra safety net is useful.
        """
        if not scores:
            return False

        latest_score = scores[-1]
        if latest_score <= 4:
            return True

        if len(scores) >= 3 and latest_score <= 5 and latest_score < scores[0]:
            return True

        distress_terms = (
            "anxiety",
            "burnout",
            "can't eat",
            "can't sleep",
            "depression",
            "distress",
            "drowning",
            "exhausted",
            "failure",
            "grief",
            "hopeless",
            "isolation",
            "lonely",
            "numb",
            "overwhelmed",
            "panic",
            "substance",
            "worthless",
        )
        recent_text = " ".join(
            [
                " ".join(entry.get("themes", []))
                + " "
                + entry.get("summary", "")
                + " "
                + entry.get("text", "")
                for entry in recent
            ]
        ).lower()

        has_distress_theme = any(term in recent_text for term in distress_terms)
        has_recurring_distress = any(
            any(term in theme.lower() for term in distress_terms)
            for theme in recurring_themes
        )

        return (has_distress_theme or has_recurring_distress) and latest_score <= 6

    def analyze_trend(self, history: list[dict], *, allow_llm_check: bool = True) -> HistoryTrend:
        """
        Analyzes the history (up to the last 5 entries) to detect trends.
        If mood is declining or consistently very low, returns a 'declining' trend.
        """
        if len(history) < 2:
            return HistoryTrend(
                trend="stable",
                reason="Not enough history to establish a trend.",
                recurring_themes=[]
            )
            
        # Get up to the last 5 entries
        recent = history[-5:]
        scores = [e["mood_score"] for e in recent]
        
        # Collect all themes and count frequencies
        theme_counts = {}
        for e in recent:
            for theme in e["themes"]:
                theme_counts[theme] = theme_counts.get(theme, 0) + 1
        
        recurring_themes = [theme for theme, count in theme_counts.items() if count >= 2]

        # Programmatic checks:
        # Rule 1: Consistently low mood (average of last 3 is <= 3.5)
        if len(scores) >= 3 and (sum(scores[-3:]) / 3.0) <= 3.5:
            return HistoryTrend(
                trend="declining",
                reason="Recent mood scores are consistently very low.",
                recurring_themes=recurring_themes
            )
            
        # Rule 2: Steady decline (e.g., scores are strictly decreasing or dropping significantly)
        # Check if the last 3 scores are strictly decreasing (e.g., 6 -> 4 -> 3)
        if len(scores) >= 3 and scores[-1] < scores[-2] < scores[-3]:
            return HistoryTrend(
                trend="declining",
                reason="Mood scores show a steady downward trajectory over the last three entries.",
                recurring_themes=recurring_themes
            )
            
        # Rule 3: Significant drop (e.g., drop of 4+ points from previous entries)
        if len(scores) >= 2 and (scores[-2] - scores[-1]) >= 4:
            return HistoryTrend(
                trend="declining",
                reason=f"Mood dropped sharply by {scores[-2] - scores[-1]} points in the last entry.",
                recurring_themes=recurring_themes
            )

        if not allow_llm_check or not self._should_run_llm_trend_check(recent, scores, recurring_themes):
            return self._calculated_trend(scores, recurring_themes)

        # Let's also run a quick LLM check on the history to see if there's a thematic decline
        # (e.g., increasing hopelessness or stress that numbers might not fully capture)
        history_summary = "\n".join([
            f"- Date: {e['timestamp'][:10]}, Mood: {e['mood_score']}/10, Themes: {', '.join(e['themes'])}, Text: {e['text']}"
            for e in recent
        ])
        
        prompt = f"""
Review the following recent journal history of a user. Determine if their emotional state is steadily declining, stable, or improving.
Look out for patterns of worsening stress, increasing isolation, feelings of hopelessness, or recurring themes of distress.

Recent History:
{history_summary}

Analyze the trend and return a JSON response matching the schema.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=HistoryTrend,
                    temperature=0.1,
                ),
            )
            data = json.loads(response.text)
            
            # If our programmatic rules already flagged it as declining, keep it as declining.
            # Otherwise, use the LLM's judgment.
            llm_trend = HistoryTrend(**data)
            if llm_trend.trend == "declining":
                return llm_trend
                
        except Exception as e:
            print(f"Error during LLM trend analysis: {e}")
            
        return self._calculated_trend(scores, recurring_themes)
