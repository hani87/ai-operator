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

app = FastAPI(title="AI Operator - Step 4 (Smarter AI)")

# --- DATABASE SETUP (zelfde als eerder) ---
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

# --- MODELS ---
class EmailRequest(BaseModel):
    subject: str
    body: str

# --- 4 VERSCHILLENDE DUMMY API'S (één per intentie) ---
def dummy_cancel(order_id: str):
    return {
        "action": "annulering",
        "order_id": order_id,
        "status": "geannuleerd",
        "message": f"Bestelling {order_id} is succesvol geannuleerd."
    }

def dummy_return(order_id: str, reason: str):
    return {
        "action": "retour",
        "order_id": order_id,
        "reason": reason,
        "status": "retour aangevraagd",
        "message": f"Retour voor {order_id} is geregistreerd. Reden: {reason}"
    }

def dummy_status(order_id: str):
    return {
        "action": "statusopvraging",
        "order_id": order_id,
        "status": "onderweg",
        "expected_delivery": "2026-09-05",
        "message": f"Bestelling {order_id} is onderweg en wordt verwacht op 5 september."
    }

def dummy_change_address(order_id: str, new_address: str):
    return {
        "action": "adreswijziging",
        "order_id": order_id,
        "new_address": new_address,
        "status": "adres bijgewerkt",
        "message": f"Het adres voor {order_id} is gewijzigd naar: {new_address}"
    }

# --- HOOFDLOGICA: AI + ROUTER ---
@app.post("/process-email")
def process_email(email: EmailRequest):
    full_text = f"Subject: {email.subject}\nBody: {email.body}"
    
    # 1. AI aanroepen met uitgebreide instructies
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """
            Je bent een AI-assistent die e-mails analyseert voor een klantenservice.
            Bepaal de intentie en haal alle relevante gegevens eruit.

            Ondersteunde intenties:
            - 'cancel' (annuleren)
            - 'return' (retourneren)
            - 'status' (statusvraag)
            - 'change_address' (adreswijziging)

            Extra velden die je kunt extraheren:
            - order_number (verplicht, string)
            - reason (optioneel, voor return)
            - new_address (optioneel, voor change_address)

            Antwoord ALTIJD in JSON met deze velden:
            {
                "intent": "cancel",
                "order_number": "12345",
                "reason": "niet tevreden met kwaliteit",
                "new_address": "Hoofdstraat 1, Amsterdam"
            }
            """},
            {"role": "user", "content": full_text}
        ],
        response_format={"type": "json_object"}
    )
    
    ai_output = json.loads(response.choices[0].message.content)
    intent = ai_output.get("intent", "unknown")
    order_number = ai_output.get("order_number")
    
    if not order_number:
        raise HTTPException(status_code=400, detail="Geen bestelnummer gevonden")
    
    # 2. Router: kies de juiste dummy-API op basis van intentie
    if intent == "cancel":
        result = dummy_cancel(order_number)
    elif intent == "return":
        reason = ai_output.get("reason", "onbekende reden")
        result = dummy_return(order_number, reason)
    elif intent == "status":
        result = dummy_status(order_number)
    elif intent == "change_address":
        new_address = ai_output.get("new_address", "onbekend adres")
        result = dummy_change_address(order_number, new_address)
    else:
        result = {
            "action": "onbekend",
            "message": f"Intentie '{intent}' wordt nog niet ondersteund."
        }
    
    # 3. Opslaan in database
    save_to_db(email.subject, email.body, intent, order_number, result)
    
    return {
        "intent": intent,
        "order_number": order_number,
        "action_result": result,
        "ai_raw": ai_output
    }

# --- HISTORY (zelfde als eerder) ---
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

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)