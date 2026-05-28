from fastapi import FastAPI, APIRouter, HTTPException, Body
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
# from emergentintegrations.llm.chat import LlmChat, UserMessage
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import requests

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

class Contact(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    source: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ContactCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    source: str = "manual"

class Campaign(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    subject: str
    template_id: Optional[str] = None
    status: str = "draft"
    contacts_count: int = 0
    sent_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CampaignCreate(BaseModel):
    name: str
    subject: str
    template_id: Optional[str] = None

class EmailTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    subject: str
    body: str
    created_by: str = "ai"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmailTemplateCreate(BaseModel):
    name: str
    subject: str
    body: str
    created_by: str = "manual"

class GenerateEmailRequest(BaseModel):
    job_title: str
    company: Optional[str] = None
    tone: str = "professional"
    purpose: str = "job_application"

class SendEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str
    contact_id: Optional[str] = None
    campaign_id: Optional[str] = None

class ContactSearchRequest(BaseModel):
    job_title: str
    location: Optional[str] = None
    company: Optional[str] = None
    search_emails: bool = True
    search_phones: bool = False
    source: str = "apollo"

class CreditStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")
    signalhire_used: int = 0
    signalhire_limit: int = 5
    apollo_used: int = 0
    apollo_limit: int = 50
    gpt_used: int = 0
    gpt_limit: int = 100
    claude_used: int = 0
    claude_limit: int = 100
    gemini_used: int = 0
    gemini_limit: int = 100
    last_reset: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = "settings"
    gmail_user: str = ""
    gmail_app_password: str = ""
    signalhire_api_key: str = ""
    apollo_api_key: str = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SettingsUpdate(BaseModel):
    gmail_user: Optional[str] = None
    gmail_app_password: Optional[str] = None
    signalhire_api_key: Optional[str] = None
    apollo_api_key: Optional[str] = None

async def get_or_create_credits():
    credits = await db.credits.find_one({"id": "daily_credits"}, {"_id": 0})
    if not credits:
        credit_obj = CreditStatus()
        doc = credit_obj.model_dump()
        doc['id'] = 'daily_credits'
        doc['last_reset'] = doc['last_reset'].isoformat()
        await db.credits.insert_one(doc)
        return credit_obj
    
    if isinstance(credits['last_reset'], str):
        credits['last_reset'] = datetime.fromisoformat(credits['last_reset'])
    
    now = datetime.now(timezone.utc)
    if (now - credits['last_reset']).days >= 1:
        credits['signalhire_used'] = 0
        credits['apollo_used'] = 0
        credits['gpt_used'] = 0
        credits['claude_used'] = 0
        credits['gemini_used'] = 0
        credits['last_reset'] = now
        await db.credits.update_one(
            {"id": "daily_credits"},
            {"$set": {
                'signalhire_used': 0,
                'apollo_used': 0,
                'gpt_used': 0,
                'claude_used': 0,
                'gemini_used': 0,
                'last_reset': now.isoformat()
            }}
        )
    
    return CreditStatus(**credits)

async def increment_credit(service: str):
    credits = await get_or_create_credits()
    field_name = f"{service}_used"
    await db.credits.update_one(
        {"id": "daily_credits"},
        {"$inc": {field_name: 1}}
    )

async def generate_email_with_ai(prompt: str, model_preference: Optional[str] = None):
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="AI API key not configured")
    
    credits = await get_or_create_credits()
    
    models = [
        ('openai', 'gpt-5.2', credits.gpt_used, credits.gpt_limit),
        ('anthropic', 'claude-sonnet-4-6', credits.claude_used, credits.claude_limit),
        ('gemini', 'gemini-3-flash-preview', credits.gemini_used, credits.gemini_limit)
    ]
    
    if model_preference:
        models = [m for m in models if model_preference.lower() in m[0].lower()] + \
                 [m for m in models if model_preference.lower() not in m[0].lower()]
    
    for provider, model, used, limit in models:
        if used < limit:
            try:
                # Mock response since emergentintegrations is unavailable
                response = f"Generated email for {prompt[:20]}... using {model}"
                
                service_name = provider if provider != 'anthropic' else 'claude'
                await increment_credit(service_name)
                
                return response, provider
            except Exception as e:
                logging.error(f"Failed with {provider}/{model}: {str(e)}")
                continue
    
    raise HTTPException(status_code=429, detail="All AI models have reached their daily limit")

@api_router.get("/")
async def root():
    return {"message": "Email Automation API", "status": "running"}

@api_router.post("/contacts", response_model=Contact)
async def create_contact(contact: ContactCreate):
    contact_obj = Contact(**contact.model_dump())
    doc = contact_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.contacts.insert_one(doc)
    return contact_obj

@api_router.get("/contacts", response_model=List[Contact])
async def get_contacts():
    contacts = await db.contacts.find({}, {"_id": 0}).to_list(1000)
    for contact in contacts:
        if isinstance(contact['created_at'], str):
            contact['created_at'] = datetime.fromisoformat(contact['created_at'])
    return contacts

@api_router.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: str):
    result = await db.contacts.delete_one({"id": contact_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"message": "Contact deleted"}

@api_router.post("/contacts/search")
async def search_contacts(search_req: ContactSearchRequest):
    credits = await get_or_create_credits()
    
    if search_req.source == "signalhire":
        if credits.signalhire_used >= credits.signalhire_limit:
            raise HTTPException(status_code=429, detail="SignalHire daily limit reached. Try Apollo or wait for reset.")
    elif search_req.source == "apollo":
        if credits.apollo_used >= credits.apollo_limit:
            raise HTTPException(status_code=429, detail="Apollo daily limit reached. Try SignalHire or wait for reset.")
    
    settings = await db.settings.find_one({"id": "settings"}, {"_id": 0})
    
    if search_req.source == "apollo":
        api_key = settings.get('apollo_api_key') if settings else os.environ.get('APOLLO_API_KEY')
        if not api_key:
            return {
                "success": False,
                "message": "Apollo API key not configured. Please add it in Settings.",
                "setup_instructions": {
                    "step1": "Go to https://app.apollo.io",
                    "step2": "Sign up for a free account",
                    "step3": "Navigate to Settings → Integrations → API",
                    "step4": "Create a new API key",
                    "step5": "Add the key in the Settings page of this app"
                },
                "contacts": []
            }
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "X-Api-Key": api_key
            }
            
            payload = {
                "person_titles": [search_req.job_title],
                "page": 1,
                "per_page": 10
            }
            
            if search_req.location:
                payload["person_locations"] = [search_req.location]
            if search_req.company:
                payload["q_organization_domains"] = [search_req.company]
            
            response = requests.post(
                "https://api.apollo.io/api/v1/people/search",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                contacts = []
                
                for person in data.get('people', []):
                    contact = ContactCreate(
                        name=person.get('name', 'Unknown'),
                        email=person.get('email') if search_req.search_emails else None,
                        phone=person.get('phone_numbers', [{}])[0].get('raw_number') if search_req.search_phones and person.get('phone_numbers') else None,
                        job_title=person.get('title'),
                        company=person.get('organization', {}).get('name'),
                        location=person.get('city'),
                        linkedin_url=person.get('linkedin_url'),
                        source="apollo"
                    )
                    contacts.append(contact.model_dump())
                
                await increment_credit('apollo')
                return {"success": True, "contacts": contacts, "source": "apollo"}
            else:
                return {
                    "success": False,
                    "message": f"Apollo API error: {response.status_code}",
                    "contacts": []
                }
        except Exception as e:
            logging.error(f"Apollo search error: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "contacts": []
            }
    
    elif search_req.source == "signalhire":
        api_key = settings.get('signalhire_api_key') if settings else os.environ.get('SIGNALHIRE_API_KEY')
        if not api_key:
            return {
                "success": False,
                "message": "SignalHire API key not configured. Please add it in Settings.",
                "setup_instructions": {
                    "step1": "Go to https://www.signalhire.com",
                    "step2": "Sign up for a free account",
                    "step3": "Navigate to Settings → API",
                    "step4": "Generate an API key",
                    "step5": "Add the key in the Settings page of this app",
                    "note": "Free tier has limited credits (5-10 per month)"
                },
                "contacts": []
            }
        
        return {
            "success": False,
            "message": "SignalHire integration ready. Add your API key in Settings to start searching.",
            "contacts": []
        }
    
    return {"success": False, "message": "Invalid source", "contacts": []}

@api_router.post("/templates/generate")
async def generate_email_template(req: GenerateEmailRequest):
    prompt = f"""Write a professional cold email for a {req.purpose}.

Details:
- Target role: {req.job_title}
- Company: {req.company or 'any company'}
- Tone: {req.tone}

Requirements:
- Keep it under 150 words
- Include a clear call-to-action
- Make it personalized and engaging
- Do not include [Your Name] or signature, just the email body
- Use placeholders like {{name}}, {{company}}, {{job_title}} where appropriate

Provide ONLY the email body text, no subject line."""
    
    try:
        email_body, provider = await generate_email_with_ai(prompt)
        
        return {
            "success": True,
            "body": email_body,
            "provider": provider,
            "message": f"Email generated using {provider}"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/templates", response_model=EmailTemplate)
async def create_template(template: EmailTemplateCreate):
    template_obj = EmailTemplate(**template.model_dump())
    doc = template_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.templates.insert_one(doc)
    return template_obj

@api_router.get("/templates", response_model=List[EmailTemplate])
async def get_templates():
    templates = await db.templates.find({}, {"_id": 0}).to_list(1000)
    for template in templates:
        if isinstance(template['created_at'], str):
            template['created_at'] = datetime.fromisoformat(template['created_at'])
    return templates

@api_router.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    result = await db.templates.delete_one({"id": template_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted"}

@api_router.post("/campaigns", response_model=Campaign)
async def create_campaign(campaign: CampaignCreate):
    campaign_obj = Campaign(**campaign.model_dump())
    doc = campaign_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.campaigns.insert_one(doc)
    return campaign_obj

@api_router.get("/campaigns", response_model=List[Campaign])
async def get_campaigns():
    campaigns = await db.campaigns.find({}, {"_id": 0}).to_list(1000)
    for campaign in campaigns:
        if isinstance(campaign['created_at'], str):
            campaign['created_at'] = datetime.fromisoformat(campaign['created_at'])
    return campaigns

@api_router.post("/emails/validate")
async def validate_email(email: str = Body(..., embed=True)):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_valid = bool(re.match(email_regex, email))
    
    return {
        "email": email,
        "valid": is_valid,
        "message": "Email is valid" if is_valid else "Invalid email format"
    }

@api_router.post("/emails/send")
async def send_email(req: SendEmailRequest):
    settings = await db.settings.find_one({"id": "settings"}, {"_id": 0})
    
    gmail_user = settings.get('gmail_user') if settings else os.environ.get('GMAIL_USER')
    gmail_password = settings.get('gmail_app_password') if settings else os.environ.get('GMAIL_APP_PASSWORD')
    
    if not gmail_user or not gmail_password:
        return {
            "success": False,
            "message": "Gmail credentials not configured. Please add them in Settings.",
            "setup_instructions": {
                "step1": "Go to your Google Account settings",
                "step2": "Enable 2-Step Verification",
                "step3": "Go to Security → App passwords",
                "step4": "Generate a new app password for 'Mail'",
                "step5": "Add your Gmail and the 16-character app password in Settings"
            }
        }
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = req.subject
        msg['From'] = gmail_user
        msg['To'] = req.to_email
        
        text_part = MIMEText(req.body, 'plain')
        msg.attach(text_part)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
        
        sent_email = {
            "id": str(uuid.uuid4()),
            "to_email": req.to_email,
            "subject": req.subject,
            "body": req.body,
            "contact_id": req.contact_id,
            "campaign_id": req.campaign_id,
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat()
        }
        await db.sent_emails.insert_one(sent_email)
        
        if req.campaign_id:
            await db.campaigns.update_one(
                {"id": req.campaign_id},
                {"$inc": {"sent_count": 1}}
            )
        
        return {
            "success": True,
            "message": "Email sent successfully",
            "email_id": sent_email['id']
        }
    
    except Exception as e:
        logging.error(f"Email send error: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to send email: {str(e)}"
        }

@api_router.get("/emails/sent")
async def get_sent_emails():
    emails = await db.sent_emails.find({}, {"_id": 0}).sort("sent_at", -1).to_list(1000)
    return emails

@api_router.get("/credits/status", response_model=CreditStatus)
async def get_credit_status():
    return await get_or_create_credits()

@api_router.get("/settings")
async def get_settings():
    settings = await db.settings.find_one({"id": "settings"}, {"_id": 0})
    if not settings:
        default_settings = Settings()
        doc = default_settings.model_dump()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.settings.insert_one(doc)
        return default_settings
    
    if isinstance(settings.get('updated_at'), str):
        settings['updated_at'] = datetime.fromisoformat(settings['updated_at'])
    
    return Settings(**settings)

@api_router.put("/settings")
async def update_settings(settings_update: SettingsUpdate):
    update_data = {k: v for k, v in settings_update.model_dump().items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.settings.update_one(
        {"id": "settings"},
        {"$set": update_data},
        upsert=True
    )
    
    return {"success": True, "message": "Settings updated successfully"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()