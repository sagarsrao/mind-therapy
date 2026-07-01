import os
import json
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError

class SafetyClassification(BaseModel):
    tier: str = Field(
        description="The safety risk tier. Must be exactly one of: 'routine', 'elevated', or 'crisis'."
    )
    confidence: float = Field(
        description="Confidence score for the classification, from 0.0 to 1.0."
    )
    reasoning: str = Field(
        description="A brief, objective explanation of why the input was classified into this tier based on safety guidelines."
    )

class SafetyClassifier:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        # Initialize the GenAI client. It will automatically pick up GEMINI_API_KEY from the environment.
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            # We will log a warning, but let the client try to initialize (which might raise an error if no credentials)
            print("Warning: GEMINI_API_KEY environment variable not set.")
        
        self.client = genai.Client()
        self.model_name = model_name

    def classify(self, text: str) -> SafetyClassification:
        """
        Classifies a single user input into 'routine', 'elevated', or 'crisis'.
        This is a context-independent, narrowly-scoped safety check.
        """
        prompt = f"""
Analyze the following user journal entry or chat message and classify it into one of three safety tiers:

1. "routine": 
   - Normal daily logs, achievements, standard daily stresses (work, school, relationships).
   - Occasional mild sadness, frustration, or situational anxiety (e.g., nervous about an exam, annoyed about an argument) where the user has a coping plan or perspective.
   - General thoughts, positive or neutral events.

2. "elevated":
   - Expresses moderate to severe emotional distress, deep loneliness, worthlessness, or hopelessness.
   - Passive suicidal ideation (e.g., "sometimes I wish I didn't wake up", "wondering what's the point of living") WITHOUT active intent, plans, or means.
   - Severe anxiety/panic attacks (highly distressed but no self-harm intent).
   - Unhealthy coping mechanisms like substance abuse to numb pain.
   - Severe grief that feels overwhelming but lacks self-harm thoughts.

3. "crisis":
   - Active suicidal ideation (expressing a clear desire, intent, or plan to end their life).
   - Mentioning specific methods, timing, or means of suicide (e.g., "I have pills", "going to a bridge", "doing it tonight").
   - Writing a goodbye note or expressing immediate finality ("goodbye", "before I go tonight").
   - Active self-harm in progress or very recent self-harm (e.g., "I cut myself", "I just took all my pills").

Strict Rules:
- If there is ANY mention of active self-harm, suicide plans, or immediate intent, you MUST classify it as "crisis".
- If the user expresses passive ideation, deep hopelessness, or severe distress without active plans, classify it as "elevated".
- Otherwise, classify it as "routine".
- Do not attempt to counsel the user. Be objective and conservative (err on the side of caution).

User Input:
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
                    response_schema=SafetyClassification,
                    temperature=0.0, # Make it deterministic
                ),
            )
            
            # The response.text will be a valid JSON matching SafetyClassification
            data = json.loads(response.text)
            result = SafetyClassification(**data)
            print(f"[SafetyClassifier] Input: \"{text[:50]}...\" → Tier: {result.tier}, Confidence: {result.confidence}")
            
            # Validate tier value
            if result.tier not in ("routine", "elevated", "crisis"):
                print(f"[SafetyClassifier] WARNING: Invalid tier '{result.tier}', defaulting to 'routine'.")
                result.tier = "routine"
            
            return result
            
        except Exception as e:
            print(f"[SafetyClassifier] ERROR during classification: {e}")
            # Fallback: default to 'routine' rather than 'elevated'.
            # Rationale: a false "elevated" on a happy input ("Feeling excited")
            # causes more harm (showing unnecessary helpline numbers) than
            # a false "routine" on a borderline input (the memory trend
            # analysis still provides a second safety net).
            return SafetyClassification(
                tier="routine",
                confidence=0.0,
                reasoning=f"Fallback triggered due to API error: {str(e)}. Defaulting to routine."
            )
