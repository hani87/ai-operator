import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query

from analyzer import EmailAnalyzer
from database import Database
from models import ActionStatus, AnalysisResult, DecisionRequest, EmailRequest

load_dotenv()

database = Database(os.getenv("DATABASE_PATH", "operator.db"))
app = FastAPI(title="AI Commitment Operator", version="0.2.0")


@app.on_event("startup")
def startup_event():
    database.init()


@app.get("/health")
def health():
    return {"status": "ok", "gmail_polling_enabled": False}


@app.post("/analyze-email", response_model=AnalysisResult)
def analyze_email(email: EmailRequest):
    try:
        analysis = EmailAnalyzer().analyze(email)
        email_id, commitment_id, action_id = database.save_analysis(email, analysis)
        return AnalysisResult(
            email_id=email_id,
            analysis=analysis,
            commitment_id=commitment_id,
            action_id=action_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/process-email", response_model=AnalysisResult, deprecated=True)
def process_email(email: EmailRequest):
    """Backward-compatible alias for the original demo endpoint."""
    return analyze_email(email)


@app.get("/commitments")
def list_commitments(status: str | None = Query(default=None)):
    return {"commitments": database.list_rows("commitments", status)}


@app.get("/actions")
def list_actions(status: str | None = Query(default=None)):
    return {"actions": database.list_rows("proposed_actions", status)}


def _decide(action_id: int, status: ActionStatus, decision: DecisionRequest):
    action = database.decide_action(action_id, status, decision.note)
    if action is None:
        raise HTTPException(
            status_code=409,
            detail="Action does not exist or is no longer pending approval",
        )
    return action


@app.post("/actions/{action_id}/approve")
def approve_action(action_id: int, decision: DecisionRequest):
    return _decide(action_id, ActionStatus.APPROVED, decision)


@app.post("/actions/{action_id}/reject")
def reject_action(action_id: int, decision: DecisionRequest):
    return _decide(action_id, ActionStatus.REJECTED, decision)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
