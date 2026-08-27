from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import json
import sqlite3
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
import uvicorn

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

app = FastAPI(title="AI Operator - Step 3 (with Database)")

# --- 1. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            body TEXT,
            intent TEXT,
            order_number TEXT,
            api_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Run this when the server starts
init_db()

def save_to_db(subject, body, intent, order_number, api_response):
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO processed_emails (subject, body, intent, order_number, api_response)
        VALUES (?, ?, ?, ?, ?)
    """, (subject, body, intent, order_number, json.dumps(api_response)))
    conn.commit()
    conn.close()

# --- 2. MODELS ---
class EmailRequest(BaseModel):
    subject: str
    body: str

# --- 3. DUMMY API ---
def dummy_api_call(order_id: str):
    return {
        "order_id": order_id,
        "status": "cancelled",
        "message": f"Order {order_id} successfully cancelled in our test system"
    }

# --- 4. MAIN PROCESSING ENDPOINT ---
@app.post("/process-email")
def process_email(email: EmailRequest):
    full_text = f"Subject: {email.subject}\nBody: {email.body}"
    
    # Call OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """
            You are an AI assistant analyzing emails.
            Determine the intent (e.g., 'cancel', 'question', 'return') 
            and extract the order number if present.
            Always respond in JSON with fields:
            - intent (string)
            - order_number (string or null)
            """},
            {"role": "user", "content": full_text}
        ],
        response_format={"type": "json_object"}
    )
    
    ai_output = json.loads(response.choices[0].message.content)
    intent = ai_output.get("intent", "unknown")
    order_number = ai_output.get("order_number")
    
    if not order_number:
        raise HTTPException(status_code=400, detail="No order number found in email")
    
    # Execute action
    result = dummy_api_call(order_number)
    
    # --- SAVE TO DATABASE ---
    save_to_db(email.subject, email.body, intent, order_number, result)
    
    return {
        "intent": intent,
        "order_number": order_number,
        "action_result": result,
        "ai_raw": ai_output
    }

# --- 5. NEW: HISTORY ENDPOINT ---
@app.get("/history")
def get_history():
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, subject, intent, order_number, created_at FROM processed_emails ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "id": row[0],
            "subject": row[1],
            "intent": row[2],
            "order_number": row[3],
            "created_at": row[4]
        })
    
    return {"total": len(history), "history": history}

# --- 6. START SERVER ---
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)