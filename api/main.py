from fastapi import FastAPI, Request
import requests
import os
import google.generativeai as genai

app = FastAPI()

# WhatsApp Cloud API credentials
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Google Gemini API credentials
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# System prompt for dental clinic
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

@app.get("/")
async def health_check():
    return {"status": "WhatsApp Dental Clinic Bot is running"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    return {"error": "Verification failed"}

@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    
    if data.get("object") == "whatsapp_business_account":
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "messages":
                    messages = change.get("value", {}).get("messages", [])
                    for message in messages:
                        sender_phone = message.get("from")
                        message_text = ""
                        
                        # Handle text messages
                        if message.get("type") == "text":
                            message_text = message.get("text", {}).get("body")
                        
                       
                        
                        # Process the message if we have text
                        if message_text:
                            # Get response from Gemini
                            gemini_response = get_gemini_response(message_text)
                            
                            # Send Gemini response back to user
                            send_message(sender_phone, gemini_response)
    
    return {"status": "ok"}


def get_gemini_response(user_message):
    try:
        # Initialize the model
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Create the conversation with system prompt
        full_prompt = f"{DENTAL_CLINIC_SYSTEM_PROMPT}\n\nUser: {user_message}\n\nAssistant:"
        
        # Generate response
        response = model.generate_content(full_prompt)
        
        return response.text
    
    except Exception as e:
        print(f"Error getting Gemini response: {e}")
        return "Sorry, I'm having trouble processing your request right now. Please call our clinic at +20 2 1234-5678 for immediate assistance."

def send_message(to_phone, message_text):
    url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"
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
        if response.status_code != 200:
            print(f"Failed to send message: {response.text}")
    except Exception as e:
        print(f"Error sending message: {e}")

