from fastapi import FastAPI, Request, HTTPException
import requests
import os
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

app = FastAPI()

# --- Configuration ---
# Load environment variables for security
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Error Handling for Configuration ---
if not all([WHATSAPP_TOKEN, PHONE_NUMBER_ID, VERIFY_TOKEN, GEMINI_API_KEY]):
    raise ValueError("One or more environment variables are missing. Please check your configuration.")

# --- Configure Google Gemini API ---
genai.configure(api_key=GEMINI_API_KEY)

# --- System Prompt (Unchanged) ---
DENTAL_CLINIC_SYSTEM_PROMPT = """
أنت مساعد مفيد لعيادة "سمايل كير للأسنان" الموجودة في القاهرة، مصر. أنت تساعد المرضى في المواعيد والمعلومات عن الخدمات والأسئلة العامة عن صحة الأسنان.

You are a helpful assistant for "SmileCare Dental Clinic" located in Cairo, Egypt. You help patients with appointments, information about services, and general dental health questions.

معلومات العيادة / CLINIC INFORMATION:
- الاسم / Name: عيادة سمايل كير للأسنان / SmileCare Dental Clinic
- الموقع / Location: القاهرة، مصر / Cairo, Egypt
- التليفون / Phone: +20 2 1234-5678
- الإيميل / Email: info@smilecare-eg.com

مواعيد العمل / WORKING HOURS:
- من السبت للخميس: 9 صباحاً - 8 مساءً / Saturday to Thursday: 9:00 AM - 8:00 PM
- الجمعة: 2 ظهراً - 8 مساءً / Friday: 2:00 PM - 8:00 PM
- خدمات الطوارئ متاحة 24/7 / Emergency services available 24/7

الخدمات والأسعار (بالجنيه المصري) / SERVICES AND PRICES (in EGP):
- كشف عام / General Consultation: 300 جنيه
- تنظيف الأسنان / Teeth Cleaning: 500 جنيه
- حشو الأسنان (للسن الواحد) / Dental Filling (per tooth): 400-800 جنيه
- علاج عصب / Root Canal Treatment: 1,500-2,500 جنيه
- خلع سن / Tooth Extraction: 600-1,200 جنيه
- تاج أسنان / Dental Crown: 2,000-4,000 جنيه
- زراعة أسنان / Dental Implant: 8,000-15,000 جنيه
- تبييض الأسنان / Teeth Whitening: 2,500 جنيه
- كشف تقويم / Orthodontic Consultation: 400 جنيه
- تقويم أسنان (العلاج كامل) / Braces (complete treatment): 15,000-25,000 جنيه
- أشعة على الأسنان / Dental X-Ray: 200 جنيه
- علاج اللثة / Gum Treatment: 800-1,500 جنيه

الأطباء / DOCTORS:
- د. أحمد حسن - طبيب أسنان عام وزراعة / Dr. Ahmed Hassan - General Dentist & Implantology
- د. فاطمة علي - أخصائية تقويم / Dr. Fatma Ali - Orthodontist
- د. محمد خالد - جراح فم وأسنان / Dr. Mohamed Khaled - Oral Surgeon
- د. نادية مصطفى - أخصائية أسنان أطفال / Dr. Nadia Mostafa - Pediatric Dentist

التعليمات المهمة / IMPORTANT GUIDELINES:
1. فهم وتحدث باللهجة المصرية العامية بطلاقة - استخدم كلمات مثل "إزيك، عامل إيه، حبيبي، يلا، خلاص، كده، أهو، برضو، عشان، لسه" إلخ
2. PERFECTLY understand Egyptian Arabic dialect including: slang, colloquial expressions, and common Egyptian phrases
3. تكون مهذب ومفيد ومهني دايماً / Always be professional, friendly, and helpful
4. تدي معلومات دقيقة عن الخدمات والأسعار / Provide accurate information about services and prices
5. لحجز موعد، اطلب: الاسم، رقم التليفون، الوقت المفضل، نوع الخدمة / For appointments, ask for: name, phone, preferred time, service type
6. لو المشكلة خطيرة، انصح بزيارة العيادة فوراً / For serious problems, recommend immediate consultation
7. قول دايماً إن الأسعار ممكن تختلف حسب الحالة / Always mention prices may vary by case
8. شجع المرضى يتصلوا للحالات الطارئة / Encourage calling for urgent issues
9. رد بالعربي لو المريض كتب بالعربي، وبالإنجليزي لو كتب بالإنجليزي / Respond in Arabic if patient writes in Arabic, English if in English
10. خلي ردودك مختصرة بس مفيدة / Keep responses concise but informative
11. لو مش عارف حاجة معينة، وجههم يتصلوا بالعيادة / If unsure about something, direct them to call the clinic

EGYPTIAN ARABIC UNDERSTANDING:
- Understand common Egyptian expressions like: "عامل إيه، إزيك، حبيبي، يا باشا، يا أستاذ، معلش، خلاص كده، أهو، برضو، عشان كده، لسه، هو كده"
- Recognize Egyptian Arabic words for body parts: "ضرس، سنة، نياب، ضواحك، نواجذ، لثة"
- Understand Egyptian complaints: "وجعني، بيوجعني، مش قادر، تعبان، مش مرتاح، مضايقني"
- Respond naturally in Egyptian dialect when appropriate

ملاحظة مهمة: إنت مش بتحجز مواعيد فعلاً - إنت بس بتدي معلومات وتوضح إزاي يحجزوا
Important Note: You cannot actually book appointments - you only provide information and guide patients on how to book.
"""

# --- FastAPI Endpoints ---

@app.get("/")
async def health_check():
    return {"status": "WhatsApp Dental Clinic Bot is running"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Verifies the webhook subscription with Meta.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return int(challenge)
    
    print("Webhook verification failed.")
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handles incoming messages from WhatsApp.
    """
    data = await request.json()
    
    try:
        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("field") == "messages":
                        messages = change.get("value", {}).get("messages", [])
                        for message in messages:
                            sender_phone = message.get("from")
                            msg_type = message.get("type")
                            
                            gemini_response = None
                            
                            if msg_type == "text":
                                message_text = message.get("text", {}).get("body")
                                if message_text:
                                    # Get response for text message
                                    gemini_response = get_gemini_response(user_message=message_text)
                            
                            # --- NEW: Handle Audio Messages ---
                            elif msg_type == "audio":
                                audio_id = message.get("audio", {}).get("id")
                                if audio_id:
                                    # 1. Get audio bytes from WhatsApp
                                    audio_bytes, mime_type = get_audio_from_whatsapp(audio_id)
                                    if audio_bytes and mime_type:
                                        # 2. Get response from Gemini using audio
                                        gemini_response = get_gemini_response(audio_bytes=audio_bytes, mime_type=mime_type)
                                    else:
                                        gemini_response = "Sorry, I couldn't process the voice note. Please try again or type your message."

                            # If we have a response, send it
                            if gemini_response:
                                send_message(sender_phone, gemini_response)
    except Exception as e:
        print(f"Error handling webhook: {e}")
        # It's good practice to still return a 200 OK to WhatsApp
        # to prevent them from resending the webhook.
    
    return {"status": "ok"}


# --- NEW: Function to get audio from WhatsApp ---
def get_audio_from_whatsapp(audio_id: str):
    """
    Fetches audio file bytes from WhatsApp servers in memory.
    Args:
        audio_id: The media ID of the audio file.
    Returns:
        A tuple of (audio_bytes, mime_type) or (None, None) if an error occurs.
    """
    # 1. Get the media URL from Meta
    url_get_media = f"https://graph.facebook.com/v20.0/{audio_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    
    try:
        media_info_response = requests.get(url_get_media, headers=headers)
        media_info_response.raise_for_status() # Raise an exception for bad status codes
        media_url = media_info_response.json().get("url")
        mime_type = media_info_response.json().get("mime_type")

        if not media_url:
            print("Error: Media URL not found in response.")
            return None, None

        # 2. Download the actual audio file bytes
        audio_response = requests.get(media_url, headers=headers)
        audio_response.raise_for_status()
        
        print(f"Successfully fetched audio. Size: {len(audio_response.content)} bytes. Mime-type: {mime_type}")
        return audio_response.content, mime_type

    except requests.exceptions.RequestException as e:
        print(f"Error fetching audio from WhatsApp: {e}")
        return None, None


# --- MODIFIED: Gemini function to handle both text and audio ---
def get_gemini_response(user_message: str = None, audio_bytes: bytes = None, mime_type: str = None):
    """
    Gets a response from Gemini, handling either a text message or audio bytes.
    """
    try:
        # Use a model that supports multimodal input, like gemini-1.5-flash
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # This prompt is added to guide the model when it receives audio
        audio_prompt = "The user has sent a voice note. Please transcribe it and then respond to their query as the helpful dental assistant, following all instructions. The audio is in Egyptian Arabic."
        
        # Prepare the content for Gemini
        content_parts = [DENTAL_CLINIC_SYSTEM_PROMPT]
        
        if audio_bytes and mime_type:
            content_parts.append(audio_prompt)
            content_parts.append({"mime_type": mime_type, "data": audio_bytes})
        elif user_message:
            content_parts.append(f"User: {user_message}\n\nAssistant:")
        else:
            return "Error: No user message or audio provided."

        # Generate response
        response = model.generate_content(
            content_parts,
            # Adding safety settings to reduce chances of the model refusing to answer
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        
        return response.text
    
    except Exception as e:
        print(f"Error getting Gemini response: {e}")
        # A generic but safe fallback message
        return "آسف، حدث خطأ أثناء معالجة طلبك. يرجى محاولة مرة أخرى أو الاتصال بالعيادة مباشرة على +20 2 1234-5678 للمساعدة الفورية.\nSorry, I encountered an error. Please try again or call our clinic directly at +20 2 1234-5678 for immediate assistance."

# --- Unchanged Helper Function ---
def send_message(to_phone: str, message_text: str):
    """
    Sends a text message to a user via the WhatsApp Cloud API.
    """
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {
            "body": message_text
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"Message sent successfully to {to_phone}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message: {e}")
        print(f"Response body: {e.response.text if e.response else 'No response'}")