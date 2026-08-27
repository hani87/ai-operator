from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import uvicorn

# Laad de API-sleutel uit .env
load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

app = FastAPI(title="AI Operator - Stap 2 (Echte AI)")

class EmailRequest(BaseModel):
    subject: str
    body: str

# De functie die de API daadwerkelijk aanroept
def dummy_api_call(order_id: str):
    return {
        "order_id": order_id,
        "status": "geannuleerd",
        "message": f"Bestelling {order_id} is succesvol geannuleerd in ons testsysteem"
    }

@app.post("/process-email")
def process_email(email: EmailRequest):
    full_text = f"Onderwerp: {email.subject}\nBericht: {email.body}"
    
    # 1. Roep OpenAI aan met een duidelijke instructie
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Goede prijs/kwaliteit
        messages=[
            {"role": "system", "content": """
            Je bent een AI-assistent die e-mails analyseert. 
            Bepaal de intentie (bijv. 'annuleren', 'vraag', 'retour') 
            en haal het bestelnummer eruit als dat er is.
            Geef je antwoord ALTIJD als JSON met de velden:
            - intentie (string)
            - bestelnummer (string of null)
            """},
            {"role": "user", "content": full_text}
        ],
        response_format={"type": "json_object"}  # Zorgt dat we altijd geldige JSON krijgen
    )
    
    # 2. Lees het AI-antwoord uit
    ai_output = json.loads(response.choices[0].message.content)
    intentie = ai_output.get("intentie", "onbekend")
    bestelnummer = ai_output.get("bestelnummer")
    
    # 3. Geef een duidelijke fout als er geen nummer is
    if not bestelnummer:
        raise HTTPException(status_code=400, detail="Geen bestelnummer gevonden in de e-mail")
    
    # 4. Voer de actie uit
    resultaat = dummy_api_call(bestelnummer)
    
    # 5. Stuur het resultaat terug
    return {
        "intentie": intentie,
        "gevonden_bestelnummer": bestelnummer,
        "actie_resultaat": resultaat,
        "ai_ruwe_output": ai_output  # Handig om te zien wat de AI precies zegt
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)