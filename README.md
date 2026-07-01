# MindTherapy

**MindTherapy** is an AI-assisted self-check-in journal for daily reflection, mood tracking, and safety-aware supportive responses.

It helps users write short journal entries, understand emotional patterns over time, and receive brief, grounded reflections without pretending to be therapy or clinical counseling. The app combines a clean journaling interface with a multi-agent FastAPI backend that classifies safety risk, analyzes mood and themes, tracks recent trends, and routes users toward appropriate support resources when needed.

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

## Features

- **Daily Check-In Journal**  
  Write short reflections about your day, mood, stress, wins, or anything on your mind.

- **AI Supportive Responses**  
  Generates brief, warm, non-clinical responses with a light follow-up question.

- **Safety-Aware Routing**  
  Classifies entries into `routine`, `elevated`, or `crisis` tiers and routes responses accordingly.

- **Mood & Theme Analysis**  
  Extracts mood scores, themes, and one-sentence summaries from journal entries.

- **Trend Detection**  
  Tracks recent entries to detect stable, improving, or declining mood patterns.

- **Recurring Theme Insights**  
  Shows topics that appear repeatedly across recent check-ins.

- **Crisis & Support Resources**  
  Surfaces immediate support options such as 988, Crisis Text Line, SAMHSA, and FindTreatment.gov when appropriate.

- **Safety Evaluation Dashboard**  
  Includes a synthetic evaluation suite to test classifier behavior across routine, elevated, and crisis examples.

- **Local JSON Storage**  
  Stores journal history locally in simple JSON files for development and demo usage.

---

## Demo Flow

Example interaction:

```text
User: I feel good after hitting the gym.
MindTherapy: It sounds like the workout gave you a real lift, and that is a useful pattern to notice. What would you like to carry from that session into the rest of your day?

User: My favorite part was cool down.
MindTherapy: Cool down and stretching sound like they gave your body a gentler landing after the workout. Did that part help you feel more relaxed or more energized?
```

---

## Tech Stack

### Backend

- **Python**
- **FastAPI**
- **Pydantic**
- **Google Gemini API** via `google-genai`
- **Uvicorn**

### Frontend

- **HTML**
- **CSS**
- **Vanilla JavaScript**
- **Chart.js**
- **Lucide Icons**

### Storage

- Local JSON files under `backend/data/`

---

## Project Structure

```text
mind-therapy/
├── backend/
│   ├── app.py
│   ├── agents/
│   │   ├── classifier.py
│   │   ├── checkin.py
│   │   ├── memory.py
│   │   └── router.py
│   ├── data/
│   │   └── history_*.json
│   └── eval/
│       ├── dataset.json
│       └── test_suite.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── requirements.txt
├── .gitignore
└── README.md
```

---

## How It Works

MindTherapy uses a small multi-agent backend pipeline:

1. **Safety Classifier**
   - Checks the current journal entry for routine, elevated, or crisis-level risk.

2. **Memory Agent**
   - Extracts mood score, themes, and summary.
   - Saves the entry locally.
   - Reviews recent history for emotional trends.

3. **Safety Router**
   - Combines current safety classification with trend analysis.
   - Chooses the appropriate response route.

4. **Check-In Agent**
   - Generates a short supportive response for routine check-ins.
   - Uses structured output validation and local fallbacks to avoid incomplete or repetitive replies.

5. **Frontend Dashboard**
   - Displays the journal chat, mood trend, recurring themes, history, and safety evaluation results.

---

## Safety Design

MindTherapy intentionally avoids acting like a therapist.

The response system is designed to:

- Avoid diagnosis.
- Avoid treatment recommendations.
- Avoid deep clinical conversations.
- Avoid probing users in crisis.
- Surface professional and crisis resources when needed.
- Keep supportive responses short, grounded, and non-clinical.

For crisis-level entries, the app prioritizes immediate support resources instead of continuing normal journaling dialogue.

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/sagarsrao/mind-therapy.git
cd mind-therapy
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

On Windows:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Do not commit `.env` to GitHub.

### 5. Run the app

```bash
python backend/app.py
```

Open:

```text
http://localhost:8000
```

---

## Running Safety Evaluations

The project includes a synthetic classifier evaluation suite.

From the UI:

1. Open the app.
2. Go to **Safety Evals**.
3. Click **Execute Test Suite**.

Or run from the command line:

```bash
python backend/eval/test_suite.py
```

The evaluation checks how the safety classifier performs across routine, elevated, and crisis-coded examples.

---

## API Endpoints

### Submit a Check-In

```http
POST /api/checkin
```

Request body:

```json
{
  "user_id": "demo-user",
  "text": "I feel good after going to the gym today."
}
```

### Get User History

```http
GET /api/history?user_id=demo-user
```

### Run Evaluation

```http
POST /api/eval/run
```

### Get Evaluation Results

```http
GET /api/eval/results
```

---

## Environment Variables

| Variable | Required | Description |
|---|---:|---|
| `GEMINI_API_KEY` | Yes | API key used by the Gemini-powered agents |
| `PORT` | No | Server port, defaults to `8000` |
| `MINDTHERAPY_AGENT_WORKERS` | No | Worker count for concurrent backend agent calls |

---

## Development Notes

- The backend serves both the API and static frontend.
- Journal history is stored locally in `backend/data/`.
- The app is optimized for local development and demos.
- For production use, replace local JSON storage with a real database and add authentication, encryption, rate limiting, and deployment-grade observability.

---

## Important Disclaimer

MindTherapy is not therapy, medical advice, diagnosis, treatment, or emergency care.

If you or someone else may be in immediate danger, call local emergency services. In the United States, call or text **988** for the Suicide & Crisis Lifeline.

---

## License

This project is currently provided for learning, prototyping, and demonstration purposes. Add a license before using it in production or accepting external contributions.

