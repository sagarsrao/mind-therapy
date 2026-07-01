import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from backend.agents.router import SafetyRouter
from backend.eval.test_suite import run_evaluation

app = FastAPI(title="MindTherapy Check-in Journal API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Router
# We will use the default data directory backend/data
router = SafetyRouter()

class CheckinRequest(BaseModel):
    user_id: str
    text: str

@app.post("/api/checkin")
async def checkin(request: CheckinRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Entry text cannot be empty.")
    try:
        result = await asyncio.to_thread(router.route_input, request.user_id, request.text)
        return result
    except Exception as e:
        print(f"Error processing check-in: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/history")
async def get_history(user_id: str):
    try:
        history = router.memory_agent.get_history(user_id)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/eval/run")
async def run_eval():
    try:
        # Run the evaluation suite
        summary = await asyncio.to_thread(run_evaluation)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run evaluation: {str(e)}")

@app.get("/api/eval/results")
async def get_eval_results():
    results_path = "backend/eval/results.json"
    if not os.path.exists(results_path):
        return {"status": "no_runs", "message": "No evaluation runs found. Please run the evaluation first."}
    try:
        with open(results_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Create the frontend directory if it doesn't exist yet
os.makedirs("frontend", exist_ok=True)

# Mount static files for the frontend
# Note: This must be at the end of the file so it doesn't override the /api routes
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    # Read port from environment or default to 8000
    port = int(os.environ.get("PORT", 8000))
    # Run the server
    print(f"Starting MindTherapy server on http://localhost:{port}")
    uvicorn.run("backend.app:app", host="0.0.0.0", port=port, reload=True)
