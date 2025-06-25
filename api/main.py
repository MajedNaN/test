from fastapi import FastAPI, Request, HTTPException
import requests
import os
import google.generativeai as genai

app = FastAPI()

# --- Configuration ---
# Load environment variables. Make sure these are set in your Vercel project settings.
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Check if all environment variables are loaded
if not all([WHATSAPP_TOKEN, PHONE_NUMBER_ID, VERIFY_TOKEN, GEMINI_API_KEY]):
    raise ValueError("Missing one or more required environment variables.")

# --- Configure Google Gemini API ---
genai.configure(api_key=GEMINI_API_KEY)

# --- System Prompt for the Dental Clinic ---
# This prompt tells Gemini how to act. It's the "brain" of your chatbot.
DENTAL_CLINIC_SYSTEM_PROMPT = """
أنت مساعد آلي ذكي لعيادة "سمايل كير للأسنان" في القاهرة. مهمتك هي الرد على استفسارات المرضى باللهجة المصرية العامية.
Your primary role is to act as a helpful AI assistant for "SmileCare Dental Clinic" in Cairo. You must respond in conversational Egyptian Arabic.

**قواعد صارمة / STRICT RULES:**
1.  **اللهجة المصرية فقط:** تحدث باللهجة المصرية العامية بطلاقة. استخدم كلمات زي "إزيك"، "عامل إيه"، "تحت أمرك"، "يا فندم"، "بص يا باشا". لازم ردودك تكون طبيعية كأنك مصري.
2.  **أنت مساعد فقط:** وضح للمريض إنك مساعد ذكي وإنك مبتعرفش تحجز مواعيد بنفسك، لكن تقدر تديله كل المعلومات اللي محتاجها عشان يحجز. قول له: "للحجز أو الطوارئ، يرجى الاتصال بنا على +20 2 1234-5678".
3.  **الأسعار والخدمات:** استخدم المعلومات الموجودة بالأسفل للرد على الأسئلة المتعلقة بالأسعار والخدمات. قول دايماً إن "الأسعار دي تقريبية وممكن تختلف حسب الحالة".
4.  **معالجة الرسائل الصوتية:** لو جاتلك رسالة صوتية، اسمعها كويس، وافهم السؤال، ورد عليه كتابةً بنفس القواعد اللي فوق.

**معلومات العيادة / CLINIC INFORMATION:**
- الاسم: عيادة سمايل كير للأسنان
- الموقع: القاهرة، مصر
- التليفون (للحجز والطوارئ): +20 2 1234-5678
- مواعيد العمل: السبت - الخميس (9ص - 8م)، الجمعة (2م - 8م)

**الخدمات والأسعار (بالجنيه المصري) / SERVICES AND PRICES (EGP):**
- كشف عام: 300
- تنظيف أسنان: 500
- حشو (للسن الواحد): يبدأ من 400
- علاج عصب: يبدأ من 1500
- خلع سن: يبدأ من 600
- زراعة أسنان: تبدأ من 8000
- تبييض أسنان: 2500
"""

# --- FastAPI Webhook Endpoints ---

@app.get("/")
def health_check():
    return {"status": "OK"}

@app.get("/webhook")
def verify_webhook(request: Request):
    """ Verifies the webhook subscription with Meta """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("WEBHOOK_VERIFIED")
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification token is invalid")

@app.post("/webhook")
async def handle_webhook(request: Request):
    """ Handles incoming messages from WhatsApp """
    data = await request.json()
    print("Received webhook:", data)  # Good for debugging

    try:
        # Check if the message is a valid WhatsApp message
        if data.get("object") and data.get("entry"):
            message = data["entry"][0]["changes"][0]["value"]["messages"][0]
            sender_phone = message["from"]
            msg_type = message["type"]

            gemini_input = []

            if msg_type == "text":
                user_text = message["text"]["body"]
                # Prepare input for Gemini
                gemini_input = [
                    DENTAL_CLINIC_SYSTEM_PROMPT,
                    f"User message: \"{user_text}\""
                ]
            
            elif msg_type == "audio":
                audio_id = message["audio"]["id"]
                # Get audio data directly from WhatsApp's servers
                audio_bytes, mime_type = get_whatsapp_media_bytes(audio_id)

                if audio_bytes:
                    # Prepare input for Gemini with the audio file
                    gemini_input = [
                        DENTAL_CLINIC_SYSTEM_PROMPT,
                        "The user sent a voice note. Transcribe it, understand the request, and answer in Egyptian Arabic based on the clinic's information.",
                        {"mime_type": mime_type, "data": audio_bytes}
                    ]
                else:
                    # If audio download fails, send an error message
                    send_message(sender_phone, "معلش، مقدرتش أسمع الرسالة الصوتية. ممكن تبعتها تاني أو تكتب سؤالك؟")
                    return {"status": "ok"}
            
            if gemini_input:
                # Get the response from Gemini
                response_text = get_gemini_response(gemini_input)
                # Send the response back to the user
                send_message(sender_phone, response_text)

    except Exception as e:
        print(f"Error handling webhook: {e}")

    return {"status": "ok"}


# --- Helper Functions ---

def get_whatsapp_media_bytes(media_id: str):
    """ Fetches media file from WhatsApp and returns its bytes and mime type """
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    
    # 1. Get Media URL
    url_get_media_info = f"https://graph.facebook.com/v20.0/{media_id}"
    try:
        media_info = requests.get(url_get_media_info, headers=headers).json()
        media_url = media_info["url"]
        mime_type = media_info["mime_type"]
        
        # 2. Download the actual audio file using the URL
        # IMPORTANT: This request also needs the auth header
        audio_response = requests.get(media_url, headers=headers)
        audio_response.raise_for_status()  # Will raise an error for bad status (4xx or 5xx)

        print(f"Successfully downloaded audio: {len(audio_response.content)} bytes, type: {mime_type}")
        return audio_response.content, mime_type
    
    except Exception as e:
        print(f"Error getting media from WhatsApp: {e}")
        return None, None

def get_gemini_response(input_parts: list):
    """
    Generates a response from Gemini using the provided input parts (text and/or audio).
    """
    try:
        # We use gemini-1.5-flash because it's fast and supports audio input.
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Generate the content
        response = model.generate_content(input_parts)
        
        # Clean up the response to ensure it's a single block of text
        return response.text.strip()
        
    except Exception as e:
        print(f"Error getting Gemini response: {e}")
        return "آسف، حصل مشكلة عندي. ممكن تكلم العيادة على طول على الرقم ده: +20 2 1234-5678"

def send_message(to_phone: str, message_text: str):
    """ Sends a text message back to the user on WhatsApp """
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "text": {"body": message_text}
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"Message sent to {to_phone}")
    except Exception as e:
        print(f"Error sending message: {e}")
        print(f"Response Body: {response.text}")