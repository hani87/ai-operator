from gmail_auth import get_gmail_service
import base64
import json
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- Database setup (zelfde als main.py) ---
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
            gmail_msg_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_to_db(subject, body, intent, order_number, api_response, gmail_msg_id):
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO processed_emails 
        (subject, body, intent, order_number, api_response, gmail_msg_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (subject, body, intent, order_number, json.dumps(api_response), gmail_msg_id))
    conn.commit()
    conn.close()

# --- Dummy API's (zelfde als main.py) ---
def dummy_cancel(order_id: str):
    return {"action": "annulering", "order_id": order_id, "status": "geannuleerd", "message": f"Bestelling {order_id} is geannuleerd."}

def dummy_return(order_id: str, reason: str):
    return {"action": "retour", "order_id": order_id, "reason": reason, "status": "retour aangevraagd", "message": f"Retour {order_id} geregistreerd. Reden: {reason}"}

def dummy_status(order_id: str):
    return {"action": "statusopvraging", "order_id": order_id, "status": "onderweg", "expected_delivery": "2026-09-05", "message": f"Bestelling {order_id} is onderweg."}

def dummy_change_address(order_id: str, new_address: str):
    return {"action": "adreswijziging", "order_id": order_id, "new_address": new_address, "status": "adres bijgewerkt", "message": f"Adres voor {order_id} gewijzigd naar {new_address}"}

# --- AI-verwerking (exact dezelfde als in main.py) ---
def process_email_content(subject: str, body: str, gmail_msg_id: str):
    full_text = f"Subject: {subject}\nBody: {body}"
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """
            Je bent een AI-assistent die e-mails analyseert voor klantenservice.
            Intenties: 'cancel', 'return', 'status', 'change_address'.
            Extra velden: order_number (verplicht), reason (optioneel), new_address (optioneel).
            Antwoord ALTIJD in JSON met deze velden.
            """},
            {"role": "user", "content": full_text}
        ],
        response_format={"type": "json_object"}
    )
    
    ai_output = json.loads(response.choices[0].message.content)
    intent = ai_output.get("intent", "unknown")
    order_number = ai_output.get("order_number")
    
    if not order_number:
        raise ValueError("Geen bestelnummer gevonden")
    
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
        result = {"action": "onbekend", "message": f"Intentie '{intent}' wordt niet ondersteund."}
    
    save_to_db(subject, body, intent, order_number, result, gmail_msg_id)
    return {"intent": intent, "order_number": order_number, "action_result": result}

# --- Hoofdscript: verwerk alle ongelezen e-mails ---
def process_unread():
    service = get_gmail_service()
    print("📡 Ophalen van ongelezen e-mails...")
    
    # Haal alle ongelezen e-mails op (max 500)
    results = service.users().messages().list(userId='me', q='is:unread', maxResults=500).execute()
    messages = results.get('messages', [])
    
    if not messages:
        print("✅ Geen ongelezen e-mails gevonden.")
        return
    
    print(f"📧 {len(messages)} ongelezen e-mails gevonden.")
    
    for msg in messages:
        msg_id = msg['id']
        print(f"📥 Verwerken: {msg_id}")
        
        # Haal volledige e-mail op
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        
        subject = "Geen onderwerp"
        body_text = ""
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        for header in headers:
            if header.get('name') == 'Subject':
                subject = header.get('value', 'Geen onderwerp')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data')
                    if data:
                        body_text = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
        else:
            data = payload.get('body', {}).get('data')
            if data:
                body_text = base64.urlsafe_b64decode(data).decode('utf-8')
        
        if not body_text:
            print(f"⚠️ Geen tekstbody, overslaan en markeren als gelezen.")
            service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
            continue
        
        # Verwerk met AI
        try:
            result = process_email_content(subject, body_text, msg_id)
            print(f"✅ Verwerkt: {result['intent']} - order {result['order_number']}")
        except Exception as e:
            print(f"❌ Fout bij verwerken: {e}")
        
        # Markeer als gelezen
        try:
            service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
            print(f"📬 Gemarkeerd als gelezen: {msg_id}")
        except Exception as e:
            print(f"⚠️ Fout bij markeren: {e}")

if __name__ == "__main__":
    init_db()  # Zorg dat de database bestaat
    process_unread()