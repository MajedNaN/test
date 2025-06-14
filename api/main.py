from fastapi import FastAPI, Request
import httpx
import os

app = FastAPI()

# Environment variables
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN") 
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

@app.get("/api/webhook")
async def verify_webhook(request: Request):
    """Verify webhook for WhatsApp"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    return "Verification failed"

@app.post("/api/webhook")
async def handle_message(request: Request):
    """Handle incoming messages and echo them back"""
    try:
        data = await request.json()
        
        # Check if there's a message
        if "entry" in data and len(data["entry"]) > 0:
            entry = data["entry"][0]
            if "changes" in entry and len(entry["changes"]) > 0:
                changes = entry["changes"][0]
                if "value" in changes:
                    value = changes["value"]
                    
                    if "messages" in value and len(value["messages"]) > 0:
                        message = value["messages"][0]
                        
                        # Only handle text messages
                        if message.get("type") == "text":
                            sender = message["from"]
                            text = message["text"]["body"]
                            
                            # Send the same message back
                            await send_message(sender, text)
    except Exception as e:
        print(f"Error: {e}")
    
    return {"status": "ok"}

async def send_message(to_number: str, message: str):
    """Send message back to WhatsApp"""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message}
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            print(f"Message sent: {response.status_code}")
    except Exception as e:
        print(f"Send error: {e}")

# Vercel handler
def handler(request):
    return app(request)