import json
import os

from openai import OpenAI

from models import EmailAnalysis, EmailRequest


SYSTEM_PROMPT = """
You are a cautious AI executive email operator. Identify commitments, decisions,
deadlines and follow-up actions. Never claim an action was executed. External
actions always require human approval. Return JSON with: category (information,
task, meeting, decision, follow_up, other), summary, contact_name,
company_or_project, commitment_title, deadline (ISO-8601 or null), urgency
(low, medium, high), proposed_action, suggested_reply, requires_approval, and
confidence (0 to 1). Use null for unknown or inapplicable fields.
"""


class EmailAnalyzer:
    def __init__(self, client=None, model: str | None = None):
        self.client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def analyze(self, request: EmailRequest) -> EmailAnalysis:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Sender: {request.sender or 'unknown'}\nSubject: {request.subject}\nBody: {request.body}"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("The model returned an empty analysis")
        return EmailAnalysis.model_validate(json.loads(content))
