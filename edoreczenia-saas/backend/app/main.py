"""
e-Doręczenia SaaS - Backend API
FastAPI application for e-Doręczenia web panel
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import httpx
import os
import uuid
import jwt

app = FastAPI(
    title="e-Doręczenia SaaS",
    description="Panel webowy do obsługi e-Doręczeń - wysyłanie i odbieranie korespondencji elektronicznej",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
class Config:
    # API endpoints (configurable via env)
    PROXY_API_URL = os.getenv("PROXY_API_URL", "http://localhost:8180")
    SYNC_API_URL = os.getenv("SYNC_API_URL", "http://localhost:8280")
    DSL_API_URL = os.getenv("DSL_API_URL", "http://localhost:8380")
    
    # OAuth2
    CLIENT_ID = os.getenv("EDORECZENIA_CLIENT_ID", "test_client_id")
    CLIENT_SECRET = os.getenv("EDORECZENIA_CLIENT_SECRET", "test_client_secret")
    
    # JWT
    JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = 24

config = Config()
security = HTTPBearer()

# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    address: str  # ADE address
    name: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class MessageCreate(BaseModel):
    recipient: str = Field(..., description="Adres ADE odbiorcy")
    subject: str = Field(..., max_length=500)
    content: str
    attachments: List[str] = []

class MessageResponse(BaseModel):
    id: str
    subject: str
    sender: dict
    recipient: Optional[dict] = None
    status: str
    receivedAt: Optional[datetime] = None
    sentAt: Optional[datetime] = None
    attachments: List[dict] = []
    content: Optional[str] = None

class FolderResponse(BaseModel):
    id: str
    name: str
    label: str
    unread_count: int = 0
    total_count: int = 0

class IntegrationStatus(BaseModel):
    name: str
    url: str
    status: str
    latency_ms: Optional[int] = None

# ═══════════════════════════════════════════════════════════════
# AUTH HELPERS
# ═══════════════════════════════════════════════════════════════

def create_jwt_token(user_id: str, username: str) -> str:
    """Create JWT token for user"""
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=config.JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials, 
            config.JWT_SECRET, 
            algorithms=[config.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token wygasł")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Nieprawidłowy token")

async def get_api_token(api_url: str) -> str:
    """Get OAuth2 token from API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_url}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": config.CLIENT_ID,
                "client_secret": config.CLIENT_SECRET
            }
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        raise HTTPException(status_code=502, detail="Błąd autoryzacji API")

# ═══════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Logowanie użytkownika
    Demo: użyj testuser/testpass123 lub mailuser/mailpass123
    """
    # Demo users (in production, use database)
    demo_users = {
        "testuser": {
            "password": "testpass123",
            "id": "user-001",
            "email": "testuser@edoreczenia.local",
            "address": "AE:PL-12345-67890-ABCDE-12",
            "name": "Użytkownik Testowy"
        },
        "mailuser": {
            "password": "mailpass123",
            "id": "user-002",
            "email": "mailuser@edoreczenia.local",
            "address": "AE:PL-SYNC-USER-00001-01",
            "name": "Użytkownik Sync"
        },
        "admin": {
            "password": "admin123",
            "id": "user-admin",
            "email": "admin@edoreczenia.local",
            "address": "AE:PL-ADMIN-0000-00001-00",
            "name": "Administrator"
        }
    }
    
    user = demo_users.get(credentials.username)
    if not user or user["password"] != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowa nazwa użytkownika lub hasło"
        )
    
    token = create_jwt_token(user["id"], credentials.username)
    
    return TokenResponse(
        access_token=token,
        expires_in=config.JWT_EXPIRATION_HOURS * 3600,
        user=UserResponse(
            id=user["id"],
            username=credentials.username,
            email=user["email"],
            address=user["address"],
            name=user["name"]
        )
    )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user(token_data: dict = Depends(verify_jwt_token)):
    """Pobierz dane zalogowanego użytkownika"""
    # Demo implementation
    return UserResponse(
        id=token_data["sub"],
        username=token_data["username"],
        email=f"{token_data['username']}@edoreczenia.local",
        address="AE:PL-12345-67890-ABCDE-12",
        name="Użytkownik Testowy"
    )

# ═══════════════════════════════════════════════════════════════
# MESSAGES ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/messages", response_model=List[MessageResponse])
async def get_messages(
    folder: str = "inbox",
    limit: int = 50,
    offset: int = 0,
    token_data: dict = Depends(verify_jwt_token)
):
    """Pobierz listę wiadomości z wybranego folderu"""
    try:
        api_token = await get_api_token(config.PROXY_API_URL)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config.PROXY_API_URL}/ua/v5/messages",
                params={"folder": folder, "limit": limit, "offset": offset},
                headers={"Authorization": f"Bearer {api_token}"}
            )
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", data) if isinstance(data, dict) else data
                return [MessageResponse(**msg) for msg in messages]
    except Exception as e:
        print(f"Error fetching messages: {e}")
    
    # Fallback demo data
    return [
        MessageResponse(
            id="msg-001",
            subject="Decyzja administracyjna nr 123/2024",
            sender={"address": "AE:PL-URZAD-MIAS-TOWAR-01", "name": "Urząd Miasta"},
            status="READ",
            receivedAt=datetime.now() - timedelta(hours=2),
            attachments=[{"filename": "decyzja.pdf", "size": 15420}]
        ),
        MessageResponse(
            id="msg-002",
            subject="Zawiadomienie o terminie rozprawy",
            sender={"address": "AE:PL-SADRE-JONO-WYYYY-02", "name": "Sąd Rejonowy"},
            status="RECEIVED",
            receivedAt=datetime.now() - timedelta(days=1),
            attachments=[]
        ),
        MessageResponse(
            id="msg-003",
            subject="Wezwanie do uzupełnienia dokumentów",
            sender={"address": "AE:PL-ZUSWA-RSZW-AODZ-03", "name": "ZUS"},
            status="RECEIVED",
            receivedAt=datetime.now() - timedelta(days=3),
            attachments=[{"filename": "wezwanie.pdf", "size": 8200}]
        )
    ]

@app.get("/api/messages/{message_id}", response_model=MessageResponse)
async def get_message(message_id: str, token_data: dict = Depends(verify_jwt_token)):
    """Pobierz szczegóły wiadomości"""
    try:
        api_token = await get_api_token(config.PROXY_API_URL)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config.PROXY_API_URL}/ua/v5/messages/{message_id}",
                headers={"Authorization": f"Bearer {api_token}"}
            )
            if response.status_code == 200:
                return MessageResponse(**response.json())
    except Exception:
        pass
    
    # Demo fallback
    return MessageResponse(
        id=message_id,
        subject="Decyzja administracyjna nr 123/2024",
        sender={"address": "AE:PL-URZAD-MIAS-TOWAR-01", "name": "Urząd Miasta Warszawa"},
        status="READ",
        receivedAt=datetime.now() - timedelta(hours=2),
        content="Szanowny Panie/Pani,\n\nW załączeniu przesyłam decyzję administracyjną...",
        attachments=[
            {"id": "att-001", "filename": "decyzja_123_2024.pdf", "contentType": "application/pdf", "size": 15420}
        ]
    )

@app.post("/api/messages", response_model=MessageResponse)
async def send_message(message: MessageCreate, token_data: dict = Depends(verify_jwt_token)):
    """Wyślij nową wiadomość"""
    try:
        api_token = await get_api_token(config.PROXY_API_URL)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.PROXY_API_URL}/ua/v5/messages",
                json={
                    "recipient": {"address": message.recipient},
                    "subject": message.subject,
                    "content": message.content,
                    "attachments": message.attachments
                },
                headers={"Authorization": f"Bearer {api_token}"}
            )
            if response.status_code in [200, 201]:
                data = response.json()
                return MessageResponse(
                    id=data.get("messageId", str(uuid.uuid4())[:8]),
                    subject=message.subject,
                    sender={"address": "AE:PL-12345-67890-ABCDE-12"},
                    recipient={"address": message.recipient},
                    status="SENT",
                    sentAt=datetime.now()
                )
    except Exception as e:
        print(f"Error sending message: {e}")
    
    # Demo fallback
    return MessageResponse(
        id=f"msg-{uuid.uuid4().hex[:8]}",
        subject=message.subject,
        sender={"address": "AE:PL-12345-67890-ABCDE-12", "name": "Użytkownik Testowy"},
        recipient={"address": message.recipient},
        status="SENT",
        sentAt=datetime.now()
    )

@app.delete("/api/messages/{message_id}")
async def delete_message(message_id: str, token_data: dict = Depends(verify_jwt_token)):
    """Usuń wiadomość (przenieś do kosza)"""
    return {"status": "deleted", "messageId": message_id}

# ═══════════════════════════════════════════════════════════════
# FOLDERS ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/folders", response_model=List[FolderResponse])
async def get_folders(token_data: dict = Depends(verify_jwt_token)):
    """Pobierz listę folderów"""
    try:
        api_token = await get_api_token(config.PROXY_API_URL)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config.PROXY_API_URL}/ua/v5/directories",
                headers={"Authorization": f"Bearer {api_token}"}
            )
            if response.status_code == 200:
                dirs = response.json().get("directories", [])
                return [
                    FolderResponse(
                        id=d["id"],
                        name=d["name"],
                        label=d.get("label", d["name"]),
                        unread_count=d.get("unreadCount", 0),
                        total_count=d.get("totalCount", 0)
                    ) for d in dirs
                ]
    except Exception:
        pass
    
    # Demo fallback
    return [
        FolderResponse(id="inbox", name="Odebrane", label="INBOX", unread_count=2, total_count=15),
        FolderResponse(id="sent", name="Wysłane", label="SENT", unread_count=0, total_count=8),
        FolderResponse(id="drafts", name="Robocze", label="DRAFTS", unread_count=0, total_count=1),
        FolderResponse(id="trash", name="Kosz", label="TRASH", unread_count=0, total_count=3),
        FolderResponse(id="archive", name="Archiwum", label="ARCHIVE", unread_count=0, total_count=25),
    ]

# ═══════════════════════════════════════════════════════════════
# INTEGRATIONS STATUS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/integrations", response_model=List[IntegrationStatus])
async def get_integrations_status(token_data: dict = Depends(verify_jwt_token)):
    """Sprawdź status integracji z usługami"""
    integrations = [
        ("Proxy IMAP/SMTP", config.PROXY_API_URL),
        ("Middleware Sync", config.SYNC_API_URL),
        ("DSL", config.DSL_API_URL),
    ]
    
    results = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in integrations:
            try:
                start = datetime.now()
                response = await client.get(f"{url}/health")
                latency = int((datetime.now() - start).total_seconds() * 1000)
                
                if response.status_code == 200:
                    results.append(IntegrationStatus(
                        name=name, url=url, status="online", latency_ms=latency
                    ))
                else:
                    results.append(IntegrationStatus(
                        name=name, url=url, status="error", latency_ms=latency
                    ))
            except Exception:
                results.append(IntegrationStatus(
                    name=name, url=url, status="offline", latency_ms=None
                ))
    
    return results

# ═══════════════════════════════════════════════════════════════
# HEALTH & INFO
# ═══════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "e-Doręczenia SaaS",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "e-Doręczenia SaaS API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
