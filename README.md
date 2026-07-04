# 🧠 MindTherapy

> **AI Agents Intensive — Vibe Coding Capstone** · Google × Kaggle · July 2026

**MindTherapy** is an AI-assisted self-check-in journal for daily reflection, mood tracking, and safety-aware supportive responses.

It helps users write short journal entries, understand emotional patterns over time, and receive brief, grounded reflections — without pretending to be therapy or clinical counseling. The app combines a clean journaling interface with a multi-agent FastAPI backend that classifies safety risk, analyzes mood and themes, tracks recent trends, and routes users toward appropriate support resources when needed.

🔗 **Live Demo: https://mind-therapy.onrender.com**

> MindTherapy is a self-reflection tool, not a replacement for professional mental health care.

---

## Why MindTherapy Exists

Most mood journals stop at logging. MindTherapy goes a step further by helping users notice patterns:

- What themes keep coming up?
- Is mood improving, stable, or declining?
- Does a check-in suggest routine reflection, elevated distress, or an urgent crisis?
- Can the app respond warmly while staying inside safe, non-clinical boundaries?

The goal is not to diagnose or treat. The goal is to make daily reflection feel easier, more consistent, and more aware.

---

## How the Four Agents Work Together

```mermaid
flowchart TD
    U([👤 User Check-in]) --> SC

    subgraph Pipeline ["Multi-Agent Pipeline"]
        SC["🔍 Safety Classifier\n─────────────────\nStateless, single-purpose\nClassifies each entry:\nROUTINE · ELEVATED · CRISIS\nFails closed on error"]
        MA["🗃️ Memory Agent\n─────────────────\nPersists check-in history\nDetects mood decline over\n5-day rolling window\nFlags recurring themes"]
        RT["🚦 Router\n─────────────────\nCombines classifier + trend\nMood-score override guard\nDetermines final route"]
        CA["💬 Check-in Agent\n─────────────────\nWarm, conversational\nOnly runs on ROUTINE route\nNever sees safety calls"]
    end

    SC --> RT
    MA --> RT
    RT -->|"ROUTINE"| CA
    RT -->|"ELEVATED"| E["🟡 Gentle Encouragement\n+ Professional Resources"]
    RT -->|"CRISIS"| C["🔴 Immediate Crisis Resources\n988 · Crisis Text Line\nNo probing · No delay"]
    CA --> R([📝 Supportive Response\n+ Trend Insight])

    style SC fill:#dbeafe,stroke:#3b82f6
    style MA fill:#dcfce7,stroke:#22c55e
    style RT fill:#fef9c3,stroke:#eab308
    style CA fill:#f3e8ff,stroke:#a855f7
    style C fill:#fee2e2,stroke:#ef4444
    style E fill:#fff7ed,stroke:#f97316
```

### Why the agents are separated

The Safety Classifier and Check-in Agent are deliberately isolated instances. A model that has been warm and agreeable across several turns is measurably more likely to soften a risk call. Separating them by design — not by prompt instruction — removes that failure mode entirely.

---

## Features

- **Daily Check-In Journal** — Write short reflections about your day, mood, stress, wins, or anything on your mind.
- **AI Supportive Responses** — Generates brief, warm, non-clinical responses with a light follow-up question.
- **Safety-Aware Routing** — Classifies entries into `routine`, `elevated`, or `crisis` tiers and routes responses accordingly.
- **Mood & Theme Analysis** — Extracts mood scores, themes, and one-sentence summaries from journal entries.
- **Trend Detection** — Tracks recent entries to detect stable, improving, or declining mood patterns.
- **Recurring Theme Insights** — Shows topics that appear repeatedly across recent check-ins.
- **Crisis & Support Resources** — Surfaces immediate support options such as 988, Crisis Text Line, SAMHSA, and FindTreatment.gov when appropriate.
- **Safety Evaluation Dashboard** — Includes a synthetic evaluation suite to test classifier behavior across routine, elevated, and crisis examples.

---

## Safety Routing in Practice

### ROUTINE — Normal check-in

> *"I feel good after hitting the gym today."*

**Classifier:** ROUTINE · **Trend:** stable
```
It sounds like the workout gave you a real lift, and that is a useful
pattern to notice. What would you like to carry from that session into
the rest of your day?
```

---

### ELEVATED — Persistent distress detected

> *"I'm exhausted. I don't know how much longer I can keep doing this. I cry in my car before going in every day."*

**Classifier:** ELEVATED · **Trend:** declining
```
I've noticed from your recent check-ins that things have been feeling
increasingly heavy. I want to gently remind you that you don't have to
go through this alone. Some free, confidential resources are listed below.

  • SAMHSA Helpline: 1-800-662-4357 (24/7, free)
  • FindTreatment.gov
  • 988 Suicide & Crisis Lifeline
```

---

### CRISIS — Immediate resource routing

> *"I can't take the pain anymore. I'm going to end my life tonight."*

**Classifier:** CRISIS
```
It sounds like you are going through a very difficult time right now.
Please know that you are not alone, and there is support available.

  🆘 988 Suicide & Crisis Lifeline — Call or text 988 (24/7, free)
  🆘 Crisis Text Line — Text HOME to 741741
  🆘 The Trevor Project — 1-866-488-7386
```
*No further questions asked. No probing. No delay.*

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Gemini 2.5 Flash (google-genai SDK) |
| Backend | FastAPI + Uvicorn |
| Agent memory | JSON persistence (swappable to Firestore) |
| Frontend | Vanilla HTML/CSS/JS + Chart.js + Lucide Icons |
| Validation | Pydantic v2 |
| Env management | python-dotenv |
| Deployment | Render (render.yaml included) |

---

## Project Structure

```
mind-therapy/
├── backend/
│   ├── app.py                  # FastAPI entry point, routes, CORS
│   ├── agents/
│   │   ├── classifier.py       # Safety Classifier — stateless, fail-closed
│   │   ├── memory.py           # Memory Agent — history, trend detection
│   │   ├── checkin.py          # Check-in Agent — warm conversational layer
│   │   └── router.py           # Router — combines all signals, enforces policy
│   ├── eval/
│   │   ├── dataset.json        # 25 synthetic test cases (7 / 10 / 8 by tier)
│   │   └── test_suite.py       # Eval runner with per-tier precision reporting
│   └── data/                   # Per-user check-in history (gitignored)
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── render.yaml                 # Render deployment config
├── .env.example                # Environment variable template
├── requirements.txt
└── README.md
```

---

## Getting Started (Local)

**Requirements:** Python 3.11+, a [Gemini API key](https://aistudio.google.com/)

```bash
# 1. Clone
git clone https://github.com/sagarsrao/mind-therapy.git
cd mind-therapy

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Run
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

> You should see `Application startup complete.` in your terminal — that confirms the server and all four agents loaded successfully.

---

## Deploying to Render

The repo includes a `render.yaml` for one-click deployment:

1. Go to [render.com](https://render.com) → **New Web Service** → connect `sagarsrao/mind-therapy`
2. Render auto-detects `render.yaml` and pre-fills build/start commands
3. Add `GEMINI_API_KEY` under the **Environment** tab
4. Click **Deploy** — live in ~3 minutes

> **Note:** The free Render tier spins down after 15 minutes of inactivity. First request after idle takes ~50 seconds to wake up.

---

## Running Safety Evaluations

The project includes a 25-case synthetic evaluation suite covering all three tiers (7 ROUTINE / 10 ELEVATED / 8 CRISIS).

From the UI: Open the app → go to **Safety Evals** → click **Execute Test Suite**

Or from the command line:
```bash
python backend/eval/test_suite.py
```

Or via the API:
```bash
curl -X POST https://mind-therapy.onrender.com/api/eval/run
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/checkin` | Submit a journal entry |
| `GET` | `/api/history?user_id=` | Retrieve check-in history |
| `POST` | `/api/eval/run` | Run the safety evaluation suite |
| `GET` | `/api/eval/results` | Get last eval results |

**POST `/api/checkin` example:**
```json
{
  "user_id": "demo-user",
  "text": "I feel good after going to the gym today."
}
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | Your Google AI Studio API key |
| `PORT` | Optional | Server port (default: `8000`) |

---

## Key Design Decisions

**The classifier is a separate agent, not a prompt instruction.** Routing safety through the same model instance that generates warm conversation creates a measurable soft-bias problem. Separation enforces the policy structurally.

**Fails closed.** Any classifier error — timeout, unparseable response, API failure — defaults to `elevated`. Ambiguous failure should never look like "all clear." The Router's mood-score override guard (score ≥ 7 downgrades `elevated` → `routine`) mitigates false positives on happy entries.

**The Memory Agent provides a second independent signal.** A user whose mood has dropped by 2+ points on average over 5 days can trigger an ELEVATED route even if today's entry alone looks manageable.

**CRISIS route has zero conversational friction.** The agent does not ask follow-up questions, does not attempt to de-escalate through dialogue, and does not encourage the user to keep journaling. It shows resources and steps aside.

---

## ⚠️ Important Disclaimer

**MindTherapy is not a medical device, clinical tool, or substitute for professional mental health care.** It is a personal journaling aid. If you or someone you know is in crisis, please contact:

- **988 Suicide & Crisis Lifeline:** Call or text **988** (US, 24/7, free)
- **Crisis Text Line:** Text **HOME** to **741741**
- **International Association for Suicide Prevention:** https://www.iasp.info/resources/Crisis_Centres/

This project was built as part of the [Google × Kaggle AI Agents Intensive Capstone](https://www.kaggle.com/competitions/vibecoding-agents-capstone-project) (June–July 2026).

---

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
