from fastapi import FastAPI, Request
import httpx
import os

app = FastAPI()

# Environment variables
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN") 
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

@app.get("/webhook")
async def verify_webhook(request: Request):
    """Verify webhook for WhatsApp"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    return "Verification failed"

@app.post("/webhook")
async def handle_message(request: Request):
    """Handle incoming messages and echo them back"""
    data = await request.json()
    
    # Check if there's a message
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        if "messages" in value:
            message = value["messages"][0]
            
            # Only handle text messages
            if message.get("type") == "text":
                sender = message["from"]
                text = message["text"]["body"]
                
                # Send the same message back
                await send_message(sender, text)
    
    except:
        pass  # Ignore any errors, just return OK
    
    return {"status": "ok"}

async def send_message(to_number: str, message: str):
    """Send message back to WhatsApp"""
    url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message}
    }
    
    async with httpx.AsyncClient() as client:
        await client.post(url, json=data, headers=headers)

# if __name__ == "__main__":
    # import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))