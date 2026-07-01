import json
import re
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class CheckinResponse(BaseModel):
    reflection: str = Field(
        description="A complete, warm, non-clinical reflection grounded in the user's entry."
    )
    question: str = Field(
        description="Exactly one short, light, open-ended follow-up question."
    )


class CheckinAgent:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.client = genai.Client()
        self.model_name = model_name

    def generate_response(
        self,
        text: str,
        trend_info: str = "",
        recurring_themes: list[str] = None,
        current_themes: list[str] = None,
        recent_entries: list[dict] = None,
    ) -> str:
        """
        Generates a warm, supportive response to the user's journal entry.
        Incorporates mood trend information and recurring themes if present.
        """
        themes_str = f"Recurring themes: {', '.join(recurring_themes)}" if recurring_themes else ""
        current_themes_str = f"Current themes: {', '.join(current_themes)}" if current_themes else ""
        recent_context = self._format_recent_entries(recent_entries or [])
        
        prompt = f"""
You are a warm, supportive, and non-judgmental check-in journal companion.
Your goal is to provide a brief, caring reflection and a light, open-ended follow-up question.

Strict Safety & Behavioral Constraints:
1. DO NOT act as a therapist, counselor, or clinical professional.
2. DO NOT provide any diagnosis (e.g., do not say "It sounds like you are depressed" or "You have anxiety").
3. DO NOT give clinical advice or treatment recommendations (e.g., do not tell them to try CBT, mindfulness, medication, or see a therapist here—this is handled by the router if concern is elevated).
4. DO NOT engage in deep reflective-listening loops that dwell on or amplify distress (e.g., do not say "I hear how incredibly dark and painful things are for you"). Acknowledge their feelings gently, but keep it brief and warm.
5. Keep the total response to 2 complete sentences: one reflection, then exactly one light, low-friction question.
6. If the user mentions recurring patterns (provided below in the context), you can gently and warm-heartedly reference them (e.g., "You've mentioned feeling stressed about work a few times this week. Would you like to talk more about that, or just log it and move on?").
7. Never return a fragment such as "That's", "Sounds", or "I hear"; every field must be a complete sentence.
8. If the entry is positive, mirror the positive moment naturally instead of sounding worried.
9. Treat the current entry as the main focus. Use recent context only to understand continuity, not to repeat a previous generic response.
10. If the current entry is a short answer to your last question, acknowledge that answer directly and ask a new, different light question.

Context:
- Current Journal Entry: "{text}"
- Mood Trend: "{trend_info}"
- {current_themes_str}
- {themes_str}
- Recent Journal Context:
{recent_context}

Return JSON only, matching the schema.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CheckinResponse,
                    temperature=0.4,
                    max_output_tokens=180
                ),
            )
            parsed = self._parse_response(response.text)
            reply = self._format_response(parsed)
            if self._is_complete_reply(reply):
                return reply

            print(f"CheckinAgent returned incomplete response: {reply!r}")
        except Exception as e:
            print(f"Error in CheckinAgent: {e}")

        return self._fallback_response(
            text,
            current_themes=current_themes,
            recurring_themes=recurring_themes,
            recent_entries=recent_entries,
        )

    def _parse_response(self, response_text: str) -> CheckinResponse:
        cleaned = (response_text or "").strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                raise
            data = json.loads(match.group(0))
        return CheckinResponse(**data)

    def _format_response(self, response: CheckinResponse) -> str:
        reflection = self._clean_sentence(response.reflection)
        question = self._clean_sentence(response.question)
        if reflection and not reflection.endswith((".", "!", "?")):
            reflection = f"{reflection}."
        if question and not question.endswith("?"):
            question = f"{question.rstrip('.!')}?"
        return f"{reflection} {question}".strip()

    def _clean_sentence(self, value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").strip().strip('"`'))

    def _format_recent_entries(self, recent_entries: list[dict]) -> str:
        if not recent_entries:
            return "  No previous entries in this session."

        lines = []
        for entry in recent_entries[-4:]:
            summary = entry.get("summary") or entry.get("text", "")
            themes = ", ".join(entry.get("themes", [])) or "none"
            lines.append(f"  - Mood {entry.get('mood_score', 'unknown')}/10; themes: {themes}; summary: {summary}")
        return "\n".join(lines)

    def _is_complete_reply(self, reply: str) -> bool:
        normalized = self._clean_sentence(reply)
        words = re.findall(r"[A-Za-z0-9']+", normalized)
        fragment_endings = (
            "i am",
            "i hear",
            "it sounds",
            "sounds",
            "that is",
            "that's",
            "you are",
            "you're",
            "you've",
        )
        compact = normalized.lower().strip(" .,!?:;")

        return (
            len(words) >= 10
            and "?" in normalized
            and not compact.endswith(fragment_endings)
            and compact not in {"that's", "that is", "sounds good", "nice", "okay"}
        )

    def _fallback_response(
        self,
        text: str,
        current_themes: list[str] = None,
        recurring_themes: list[str] = None,
        recent_entries: list[dict] = None,
    ) -> str:
        lower_text = text.lower()
        themes = [theme.lower() for theme in (current_themes or [])]
        current_context = " ".join([lower_text, *themes])
        recent_text = " ".join(
            [
                entry.get("text", "")
                + " "
                + entry.get("summary", "")
                + " "
                + " ".join(entry.get("themes", []))
                for entry in (recent_entries or [])
            ]
        ).lower()

        def has_any(source: str, terms: tuple[str, ...]) -> bool:
            return any(term in source for term in terms)

        positive_terms = ("good", "great", "happy", "happiness", "excited", "proud", "better", "calm", "peaceful", "satisfied")
        exercise_terms = ("gym", "workout", "exercise", "run", "walk", "training")
        recovery_terms = ("cool down", "cooldown", "stretch", "stretching", "mobility")
        strength_terms = ("strength", "conditioning", "weights", "lifting")

        if has_any(current_context, strength_terms):
            return (
                "That mix of stretching, strength, and conditioning sounds like it helped you reconnect with your body in a strong way. "
                "What part of that strength felt most noticeable today?"
            )

        if has_any(current_context, recovery_terms):
            return (
                "Cool down and stretching sound like they gave your body a gentler landing after the workout. "
                "Did that part help you feel more relaxed or more energized?"
            )

        if has_any(current_context, ("happiness", "happy")):
            if has_any(recent_text, ("gym", "workout", "exercise", "cool down", "stretch", "strength")):
                return (
                    "Happiness is a clear and simple thing to log, especially after noticing how movement helped you feel stronger. "
                    "What do you think contributed most to that happiness today?"
                )
            return (
                "Happiness is a good moment to capture, and I have logged it for you. "
                "What do you think contributed most to it today?"
            )

        if has_any(current_context, exercise_terms):
            return (
                "It sounds like the workout gave you a real lift, and that is a useful pattern to notice. "
                "What would you like to carry from that session into the rest of your day?"
            )

        if has_any(current_context, positive_terms):
            return (
                "I am glad there was something positive in your day, and I have logged that moment for you. "
                "What do you want to remember about it?"
            )

        if has_any(current_context, ("work", "office", "job", "deadline", "meeting")):
            return (
                "It sounds like work is taking up some space in your mind today, and I have logged that clearly. "
                "Do you want to unpack it a little, or just mark it and move on?"
            )

        if has_any(current_context, ("stress", "stressed", "anxious", "overwhelmed", "tired", "exhausted")):
            return (
                "That sounds like a heavier check-in, and I am glad you wrote it down here. "
                "What is the smallest part of it you want to name right now?"
            )

        return (
            "Thank you for sharing that; I have logged this check-in as part of your journal. "
            "What feels most worth remembering about it?"
        )
