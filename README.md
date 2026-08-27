# 🤖 AI Email Operator

An intelligent system that reads emails, understands intent, and automatically executes actions via API calls.  
Built as the first step toward a "Jarvis" for business automation.

---

## 🎯 What it does

- Receives an email (subject + body)
- AI determines the intent (cancel, return, question, etc.)
- Extracts structured data (order numbers, dates, etc.)
- Executes an action via an API call
- Returns a structured JSON response
- **NEW:** Stores everything in a database for history tracking

---

## 🧪 Example

**Input (JSON):**
```json
{
  "subject": "Cancellation",
  "body": "I want to cancel my order 12345"
}

{
  "intent": "cancel",
  "order_number": "12345",
  "action_result": {
    "order_id": "12345",
    "status": "cancelled",
    "message": "Order 12345 successfully cancelled in our test system"
  }
}

# Clone the repository
git clone https://github.com/your-username/ai-email-operator.git
cd ai-email-operator

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt