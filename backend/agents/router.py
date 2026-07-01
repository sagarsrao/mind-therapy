import os
import time
from concurrent.futures import ThreadPoolExecutor

from backend.agents.classifier import SafetyClassifier
from backend.agents.memory import MemoryAgent
from backend.agents.checkin import CheckinAgent

class SafetyRouter:
    def __init__(self, data_dir: str = "backend/data", model_name: str = "gemini-2.5-flash"):
        self.classifier = SafetyClassifier(model_name=model_name)
        self.memory_agent = MemoryAgent(data_dir=data_dir, model_name=model_name)
        self.checkin_agent = CheckinAgent(model_name=model_name)
        try:
            max_workers = max(2, int(os.environ.get("MINDTHERAPY_AGENT_WORKERS", "4")))
        except ValueError:
            max_workers = 4
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def route_input(self, user_id: str, text: str) -> dict:
        """
        Processes a user input through the multi-agent pipeline and returns the routed response.
        """
        start_time = time.perf_counter()

        # 1. Run independent model-backed checks concurrently.
        classification_future = self.executor.submit(self.classifier.classify, text)
        entry_analysis_future = self.executor.submit(self.memory_agent.analyze_entry, text)

        classification = classification_future.result()
        entry_analysis = entry_analysis_future.result()
        
        # 2. Update memory and analyze trend (Context-aware).
        # Crisis/elevated current inputs already get resource routing below, so the
        # slower thematic history check is only needed for otherwise routine inputs.
        recent_entries = self.memory_agent.get_recent_history(user_id, limit=4)
        entry = self.memory_agent.build_entry(text, entry_analysis)
        entry, trend_analysis = self.memory_agent.append_entry_and_analyze_trend(
            user_id,
            entry,
            allow_llm_trend_check=classification.tier == "routine",
        )
        
        # 3. Determine Route
        route = "routine"
        response_text = ""
        resources = []
        
        # Crisis Resources
        CRISIS_RESOURCES = [
            {
                "name": "988 Suicide & Crisis Lifeline",
                "description": "Free, confidential, 24/7 support for anyone in suicidal crisis or emotional distress.",
                "phone": "988",
                "text": "Text 988",
                "url": "https://988lifeline.org/"
            },
            {
                "name": "The Trevor Project (LGBTQ+)",
                "phone": "1-866-488-7386",
                "text": "Text START to 678-678",
                "url": "https://www.thetrevorproject.org/"
            },
            {
                "name": "Crisis Text Line",
                "text": "Text HOME to 741741",
                "url": "https://www.crisistextline.org/"
            }
        ]
        
        # Elevated Concern Resources
        SUPPORT_RESOURCES = [
            {
                "name": "SAMHSA’s National Helpline",
                "description": "Free, confidential, 24/7 treatment referral and information service.",
                "phone": "1-800-662-4357",
                "url": "https://www.samhsa.gov/find-help/national-helpline"
            },
            {
                "name": "FindTreatment.gov",
                "description": "Find state-licensed providers who specialize in treating substance use disorders and mental health issues.",
                "url": "https://findtreatment.gov/"
            }
        ]

        if classification.tier == "crisis":
            # Crisis Route: Immediately surface resources, no dialogue, no probing, no attempt to keep them talking.
            route = "crisis"
            response_text = (
                "It sounds like you are going through a very difficult time right now. "
                "Please know that you are not alone, and there is support available. "
                "We have provided immediate, free, and confidential crisis resources below. "
                "Please reach out to one of them right now. They are here to help."
            )
            resources = CRISIS_RESOURCES
            
        elif classification.tier == "elevated" or trend_analysis.trend == "declining":
            # Guard: if the user's current mood is clearly positive (score >= 7),
            # do NOT route to elevated — the classifier or trend was likely wrong.
            current_mood = entry["mood_score"]
            if current_mood >= 7 and classification.tier != "crisis":
                print(f"[Router] Override: classifier={classification.tier}, trend={trend_analysis.trend}, "
                      f"but mood_score={current_mood} is positive. Routing to 'routine' instead.")
                route = "routine"
                trend_info = f"User mood is {trend_analysis.trend}. {trend_analysis.reason}"
                response_text = self.checkin_agent.generate_response(
                    text=text,
                    trend_info=trend_info,
                    recurring_themes=trend_analysis.recurring_themes,
                    current_themes=entry["themes"],
                    recent_entries=recent_entries,
                )
                resources = []
            else:
                # Elevated Concern Route: Gently encourage professional support.
                route = "elevated"
                
                # Formulate a gentle response acknowledging the situation and providing resources
                reason_str = ""
                if trend_analysis.trend == "declining":
                    reason_str = "I've noticed from your recent check-ins that things have been feeling increasingly heavy or stressful. "
                else:
                    reason_str = "It sounds like you are carrying a lot of stress or difficult emotions today. "
                    
                response_text = (
                    f"{reason_str}I want to gently remind you that you don't have to go through this alone. "
                    "While this journal is a safe space to log your thoughts, it isn't a substitute for professional care. "
                    "If you feel comfortable, please consider reaching out to a professional or talking to someone who can support you. "
                    "We've listed some free, confidential resources below."
                )
                # Combine both support and crisis resources just in case, but prioritize support
                resources = SUPPORT_RESOURCES + [CRISIS_RESOURCES[0]]
            
        else:
            # Routine Route: Normal supportive reflection and follow-up
            route = "routine"
            # Format trend info for the checkin agent
            trend_info = f"User mood is {trend_analysis.trend}. {trend_analysis.reason}"
            response_text = self.checkin_agent.generate_response(
                text=text,
                trend_info=trend_info,
                recurring_themes=trend_analysis.recurring_themes,
                current_themes=entry["themes"],
                recent_entries=recent_entries,
            )
            resources = []

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        print(
            f"[Router] Final route: {route} | Classifier: {classification.tier} | "
            f"Trend: {trend_analysis.trend} | Mood: {entry['mood_score']} | "
            f"Elapsed: {elapsed_ms:.0f}ms"
        )

        return {
            "route": route,
            "response": response_text,
            "resources": resources,
            "classifier_result": {
                "tier": classification.tier,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning
            },
            "trend_result": {
                "trend": trend_analysis.trend,
                "reason": trend_analysis.reason,
                "recurring_themes": trend_analysis.recurring_themes
            },
            "entry_analysis": {
                "mood_score": entry["mood_score"],
                "themes": entry["themes"],
                "summary": entry["summary"]
            }
        }
print("Router module successfully loaded.")
