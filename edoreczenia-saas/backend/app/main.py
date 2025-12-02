"""
e-Doręczenia SaaS - Backend API
FastAPI application for e-Doręczenia web panel

Architecture: CQRS + Event Sourcing
- Commands: Write operations that generate events
- Queries: Read operations from projections
- Events: Immutable facts stored in Event Store
- Projections: Read models built from events
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import httpx
import os
import uuid
import jwt

# Database
from .database import init_db, get_db

# Services (SQLite)
from .services.message_service import message_service
from .services.integration_service import integration_service
from .services.user_service import user_service

# CQRS imports
from .cqrs.commands import (
    CreateMessageCommand, SendMessageCommand, ReadMessageCommand,
    ArchiveMessageCommand, DeleteMessageCommand, MoveMessageCommand,
    LoginCommand, StartSyncCommand
)
from .cqrs.queries import (
    GetMessagesQuery, GetMessageQuery, GetMessageHistoryQuery,
    GetFoldersQuery, GetUserActivityQuery, GetEventLogQuery, GetDashboardStatsQuery
)
from .cqrs.command_handlers import command_bus
from .cqrs.query_handlers import query_bus
from .cqrs.event_store import event_store
from .cqrs.events import MessageReceivedEvent
from .cqrs.projections import message_projection, folder_projection

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
# E-DORĘCZENIA ADDRESS INTEGRATION MODELS
# ═══════════════════════════════════════════════════════════════

class AddressIntegrationRequest(BaseModel):
    """Żądanie integracji adresu e-Doręczeń"""
    ade_address: str = Field(..., description="Adres ADE (np. AE:PL-12345-67890-ABCDE-12)")
    provider: str = Field(default="certum", description="Dostawca: certum, poczta_polska")
    auth_method: str = Field(..., description="Metoda uwierzytelnienia: mobywatel, certum_signature, qualified_signature")
    # Dane do weryfikacji
    nip: Optional[str] = None
    pesel: Optional[str] = None
    krs: Optional[str] = None
    regon: Optional[str] = None
    entity_type: str = Field(default="person", description="Typ: person, company, public_entity")

class AddressIntegrationResponse(BaseModel):
    """Odpowiedź integracji adresu"""
    id: str
    ade_address: str
    status: str  # pending, verifying, active, failed
    provider: str
    entity_type: str
    created_at: datetime
    verified_at: Optional[datetime] = None
    message: Optional[str] = None

class AddressVerificationStep(BaseModel):
    """Krok weryfikacji"""
    step: int
    name: str
    status: str  # pending, in_progress, completed, failed
    description: str
    required_action: Optional[str] = None

class IntegrationCredentials(BaseModel):
    """Poświadczenia do integracji"""
    integration_id: str
    oauth_token: Optional[str] = None
    certificate_thumbprint: Optional[str] = None
    api_key: Optional[str] = None
    expires_at: Optional[datetime] = None

# In-memory storage for integrations (w produkcji: baza danych)
address_integrations = {}

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
    """Pobierz listę wiadomości z wybranego folderu - SQLite + demo data"""
    user_id = token_data["sub"]
    result_messages = []
    
    # 1. Pobierz wiadomości z SQLite
    db_messages = message_service.get_messages(
        user_id=user_id,
        folder=folder,
        limit=limit,
        offset=offset
    )
    
    for msg in db_messages:
        result_messages.append(MessageResponse(
            id=msg.id,
            subject=msg.subject,
            sender={"address": msg.sender_address or "unknown", "name": msg.sender_name},
            recipient={"address": msg.recipient_address} if msg.recipient_address else None,
            status=msg.status,
            receivedAt=msg.received_at,
            sentAt=msg.sent_at,
            content=msg.content,
            attachments=msg.attachments or []
        ))
    
    # 2. Próba pobrania z zewnętrznego API
    try:
        api_token = await get_api_token(config.PROXY_API_URL)
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(
                f"{config.PROXY_API_URL}/ua/v5/messages",
                params={"folder": folder, "limit": limit, "offset": offset},
                headers={"Authorization": f"Bearer {api_token}"}
            )
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", data) if isinstance(data, dict) else data
                for msg in messages:
                    result_messages.append(MessageResponse(**msg))
    except Exception as e:
        print(f"External API unavailable: {e}")
    
    # Fallback demo data - różne dla każdego folderu
    demo_messages = {
        "inbox": [
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
        ],
        "sent": [
            MessageResponse(
                id="msg-sent-001",
                subject="Odpowiedź na decyzję nr 123/2024",
                sender={"address": "AE:PL-12345-67890-ABCDE-12", "name": "Użytkownik Testowy"},
                recipient={"address": "AE:PL-URZAD-MIAS-TOWAR-01", "name": "Urząd Miasta"},
                status="SENT",
                sentAt=datetime.now() - timedelta(hours=5),
                attachments=[]
            ),
            MessageResponse(
                id="msg-sent-002",
                subject="Wniosek o wydanie zaświadczenia",
                sender={"address": "AE:PL-12345-67890-ABCDE-12", "name": "Użytkownik Testowy"},
                recipient={"address": "AE:PL-ZUSWA-RSZW-AODZ-03", "name": "ZUS"},
                status="DELIVERED",
                sentAt=datetime.now() - timedelta(days=2),
                attachments=[{"filename": "wniosek.pdf", "size": 12300}]
            )
        ],
        "drafts": [
            MessageResponse(
                id="msg-draft-001",
                subject="[Robocza] Odwołanie od decyzji",
                sender={"address": "AE:PL-12345-67890-ABCDE-12", "name": "Użytkownik Testowy"},
                status="DRAFT",
                receivedAt=datetime.now() - timedelta(hours=1),
                attachments=[]
            )
        ],
        "trash": [
            MessageResponse(
                id="msg-trash-001",
                subject="Stara korespondencja - do usunięcia",
                sender={"address": "AE:PL-FIRMA-XXXX-YYYY-01", "name": "Firma XYZ"},
                status="READ",
                receivedAt=datetime.now() - timedelta(days=30),
                attachments=[]
            ),
            MessageResponse(
                id="msg-trash-002",
                subject="Nieaktualne powiadomienie",
                sender={"address": "AE:PL-URZAD-SKAR-BOWY-01", "name": "Urząd Skarbowy"},
                status="READ",
                receivedAt=datetime.now() - timedelta(days=45),
                attachments=[{"filename": "stary_dokument.pdf", "size": 5400}]
            )
        ],
        "archive": [
            MessageResponse(
                id="msg-arch-001",
                subject="Potwierdzenie złożenia deklaracji PIT-37",
                sender={"address": "AE:PL-URZAD-SKAR-BOWY-01", "name": "Urząd Skarbowy"},
                status="READ",
                receivedAt=datetime.now() - timedelta(days=90),
                attachments=[{"filename": "UPO_PIT37.pdf", "size": 25000}]
            ),
            MessageResponse(
                id="msg-arch-002",
                subject="Decyzja o przyznaniu świadczenia",
                sender={"address": "AE:PL-ZUSWA-RSZW-AODZ-03", "name": "ZUS"},
                status="READ",
                receivedAt=datetime.now() - timedelta(days=120),
                attachments=[{"filename": "decyzja_swiadczenie.pdf", "size": 18700}]
            ),
            MessageResponse(
                id="msg-arch-003",
                subject="Zaświadczenie o niezaleganiu",
                sender={"address": "AE:PL-URZAD-SKAR-BOWY-01", "name": "Urząd Skarbowy"},
                status="READ",
                receivedAt=datetime.now() - timedelta(days=180),
                attachments=[{"filename": "zaswiadczenie.pdf", "size": 9800}]
            )
        ]
    }
    
    # 3. Dodaj demo data jeśli brak wiadomości z CQRS
    if not result_messages:
        result_messages = demo_messages.get(folder, demo_messages["inbox"])
    else:
        # Dodaj demo data na koniec
        result_messages.extend(demo_messages.get(folder, []))
    
    return result_messages

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
    
    # Demo fallback - szczegóły wiadomości
    demo_details = {
        "msg-001": MessageResponse(
            id="msg-001",
            subject="Decyzja administracyjna nr 123/2024",
            sender={"address": "AE:PL-URZAD-MIAS-TOWAR-01", "name": "Urząd Miasta Warszawa"},
            status="READ",
            receivedAt=datetime.now() - timedelta(hours=2),
            content="Szanowny Panie/Pani,\n\nNa podstawie art. 104 Kodeksu postępowania administracyjnego, po rozpatrzeniu wniosku z dnia 15.11.2024 r., orzekam:\n\n1. Zatwierdzam projekt budowlany dotyczący rozbudowy budynku mieszkalnego.\n2. Decyzja jest ostateczna i podlega wykonaniu.\n\nPouczenie:\nOd niniejszej decyzji przysługuje odwołanie do Samorządowego Kolegium Odwoławczego w terminie 14 dni od daty doręczenia.\n\nZ poważaniem,\nJan Kowalski\nNaczelnik Wydziału",
            attachments=[
                {"id": "att-001", "filename": "decyzja_123_2024.pdf", "contentType": "application/pdf", "size": 15420}
            ]
        ),
        "msg-002": MessageResponse(
            id="msg-002",
            subject="Zawiadomienie o terminie rozprawy",
            sender={"address": "AE:PL-SADRE-JONO-WYYYY-02", "name": "Sąd Rejonowy"},
            status="RECEIVED",
            receivedAt=datetime.now() - timedelta(days=1),
            content="ZAWIADOMIENIE\n\nSąd Rejonowy w Warszawie, Wydział Cywilny zawiadamia, że rozprawa w sprawie sygn. akt I C 1234/24 odbędzie się w dniu 15.01.2025 r. o godz. 10:00 w sali nr 205.\n\nStawiennictwo obowiązkowe.\n\nSekretariat Sądu",
            attachments=[]
        ),
        "msg-003": MessageResponse(
            id="msg-003",
            subject="Wezwanie do uzupełnienia dokumentów",
            sender={"address": "AE:PL-ZUSWA-RSZW-AODZ-03", "name": "ZUS Oddział Warszawa"},
            status="RECEIVED",
            receivedAt=datetime.now() - timedelta(days=3),
            content="Szanowny Płatniku,\n\nW związku z prowadzonym postępowaniem wzywamy do uzupełnienia dokumentacji w terminie 7 dni od daty doręczenia niniejszego pisma.\n\nWymagane dokumenty:\n- Zaświadczenie o zatrudnieniu\n- Kopia umowy o pracę\n- Druk ZUS ZUA\n\nBrak odpowiedzi skutkować będzie wydaniem decyzji na podstawie posiadanych dokumentów.\n\nZ poważaniem,\nZUS Oddział w Warszawie",
            attachments=[
                {"id": "att-003", "filename": "wezwanie.pdf", "contentType": "application/pdf", "size": 8200}
            ]
        ),
        "msg-sent-001": MessageResponse(
            id="msg-sent-001",
            subject="Odpowiedź na decyzję nr 123/2024",
            sender={"address": "AE:PL-12345-67890-ABCDE-12", "name": "Użytkownik Testowy"},
            recipient={"address": "AE:PL-URZAD-MIAS-TOWAR-01", "name": "Urząd Miasta"},
            status="SENT",
            sentAt=datetime.now() - timedelta(hours=5),
            content="Szanowni Państwo,\n\nW odpowiedzi na decyzję nr 123/2024 informuję, że akceptuję jej treść i przystępuję do realizacji.\n\nZ poważaniem",
            attachments=[]
        ),
        "msg-sent-002": MessageResponse(
            id="msg-sent-002",
            subject="Wniosek o wydanie zaświadczenia",
            sender={"address": "AE:PL-12345-67890-ABCDE-12", "name": "Użytkownik Testowy"},
            recipient={"address": "AE:PL-ZUSWA-RSZW-AODZ-03", "name": "ZUS"},
            status="DELIVERED",
            sentAt=datetime.now() - timedelta(days=2),
            content="Wnoszę o wydanie zaświadczenia o niezaleganiu w opłacaniu składek ZUS.\n\nDane wnioskodawcy:\nNIP: 1234567890\nREGON: 123456789",
            attachments=[
                {"id": "att-sent-002", "filename": "wniosek.pdf", "contentType": "application/pdf", "size": 12300}
            ]
        ),
        "msg-draft-001": MessageResponse(
            id="msg-draft-001",
            subject="[Robocza] Odwołanie od decyzji",
            sender={"address": "AE:PL-12345-67890-ABCDE-12", "name": "Użytkownik Testowy"},
            status="DRAFT",
            receivedAt=datetime.now() - timedelta(hours=1),
            content="Niniejszym składam odwołanie od decyzji...\n\n[WERSJA ROBOCZA - DO UZUPEŁNIENIA]",
            attachments=[]
        ),
        "msg-trash-001": MessageResponse(
            id="msg-trash-001",
            subject="Stara korespondencja - do usunięcia",
            sender={"address": "AE:PL-FIRMA-XXXX-YYYY-01", "name": "Firma XYZ"},
            status="READ",
            receivedAt=datetime.now() - timedelta(days=30),
            content="Oferta handlowa - nieaktualna",
            attachments=[]
        ),
        "msg-arch-001": MessageResponse(
            id="msg-arch-001",
            subject="Potwierdzenie złożenia deklaracji PIT-37",
            sender={"address": "AE:PL-URZAD-SKAR-BOWY-01", "name": "Urząd Skarbowy"},
            status="READ",
            receivedAt=datetime.now() - timedelta(days=90),
            content="Urzędowe Poświadczenie Odbioru\n\nPotwierdzamy przyjęcie deklaracji PIT-37 za rok 2023.\nNumer referencyjny: UPO/2024/123456\nData złożenia: 2024-04-15",
            attachments=[
                {"id": "att-arch-001", "filename": "UPO_PIT37.pdf", "contentType": "application/pdf", "size": 25000}
            ]
        )
    }
    
    if message_id in demo_details:
        return demo_details[message_id]
    
    # Domyślna odpowiedź dla nieznanych ID
    return MessageResponse(
        id=message_id,
        subject=f"Wiadomość {message_id}",
        sender={"address": "AE:PL-UNKNOWN-0000-0000-00", "name": "Nieznany nadawca"},
        status="READ",
        receivedAt=datetime.now(),
        content="Treść wiadomości niedostępna.",
        attachments=[]
    )

@app.post("/api/messages", response_model=MessageResponse)
async def send_message(message: MessageCreate, token_data: dict = Depends(verify_jwt_token)):
    """Wyślij nową wiadomość - zapisuje do SQLite + CQRS Event Store"""
    user_id = token_data["sub"]
    
    # 1. Zapisz wiadomość do SQLite
    db_message = message_service.create_message(
        user_id=user_id,
        subject=message.subject,
        content=message.content,
        recipient_address=message.recipient,
        folder="drafts",
        status="DRAFT"
    )
    
    # 2. Wyślij wiadomość (zmień status)
    db_message = message_service.send_message(db_message.id)
    
    # 3. Zapisz zdarzenie do Event Store (CQRS)
    create_cmd = CreateMessageCommand(
        user_id=user_id,
        recipient=message.recipient,
        subject=message.subject,
        content=message.content,
        attachments=message.attachments
    )
    create_result = await command_bus.dispatch(create_cmd)
    
    if create_result.success:
        send_cmd = SendMessageCommand(
            user_id=user_id,
            message_id=create_result.data["message_id"]
        )
        await command_bus.dispatch(send_cmd)
    
    # 4. Próba wysłania przez zewnętrzne API (opcjonalne)
    try:
        api_token = await get_api_token(config.PROXY_API_URL)
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{config.PROXY_API_URL}/ua/v5/messages",
                json={
                    "recipient": {"address": message.recipient},
                    "subject": message.subject,
                    "content": message.content,
                    "attachments": message.attachments
                },
                headers={"Authorization": f"Bearer {api_token}"}
            )
    except Exception as e:
        print(f"External API unavailable: {e}")
    
    # Zwróć odpowiedź z SQLite
    return MessageResponse(
        id=db_message.id,
        subject=db_message.subject,
        sender={"address": db_message.sender_address or "unknown", "name": db_message.sender_name or "Użytkownik"},
        recipient={"address": db_message.recipient_address},
        status=db_message.status,
        sentAt=db_message.sent_at,
        content=db_message.content
    )

@app.delete("/api/messages/{message_id}")
async def delete_message(message_id: str, token_data: dict = Depends(verify_jwt_token)):
    """Usuń wiadomość (przenieś do kosza)"""
    return {"status": "deleted", "messageId": message_id}

@app.post("/api/messages/{message_id}/archive")
async def archive_message(message_id: str, token_data: dict = Depends(verify_jwt_token)):
    """Przenieś wiadomość do archiwum"""
    return {"status": "archived", "messageId": message_id, "folder": "archive"}

@app.post("/api/messages/{message_id}/move")
async def move_message(message_id: str, data: dict, token_data: dict = Depends(verify_jwt_token)):
    """Przenieś wiadomość do innego folderu"""
    folder = data.get("folder", "inbox")
    return {"status": "moved", "messageId": message_id, "folder": folder}

@app.post("/api/messages/{message_id}/read")
async def mark_as_read(message_id: str, token_data: dict = Depends(verify_jwt_token)):
    """Oznacz wiadomość jako przeczytaną"""
    return {"status": "read", "messageId": message_id}

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
# ADDRESS INTEGRATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/address-integrations", response_model=List[AddressIntegrationResponse])
async def get_address_integrations(token_data: dict = Depends(verify_jwt_token)):
    """Pobierz listę zintegrowanych adresów e-Doręczeń - SQLite"""
    user_id = token_data["sub"]
    integrations = integration_service.get_integrations(user_id)
    return [
        AddressIntegrationResponse(**integration_service.to_response_dict(i))
        for i in integrations
    ]


@app.post("/api/address-integrations", response_model=AddressIntegrationResponse)
async def create_address_integration(
    request: AddressIntegrationRequest,
    token_data: dict = Depends(verify_jwt_token)
):
    """Rozpocznij integrację adresu e-Doręczeń - SQLite"""
    user_id = token_data["sub"]
    
    # Walidacja adresu ADE
    if not request.ade_address.startswith("AE:PL-"):
        raise HTTPException(
            status_code=400, 
            detail="Nieprawidłowy format adresu ADE. Powinien zaczynać się od 'AE:PL-'"
        )
    
    # Walidacja danych identyfikacyjnych
    if request.entity_type == "person" and not request.pesel:
        raise HTTPException(status_code=400, detail="PESEL jest wymagany dla osób fizycznych")
    if request.entity_type == "company" and not (request.nip or request.krs):
        raise HTTPException(status_code=400, detail="NIP lub KRS jest wymagany dla firm")
    
    integration = integration_service.create_integration(
        user_id=user_id,
        ade_address=request.ade_address,
        provider=request.provider,
        auth_method=request.auth_method,
        entity_type=request.entity_type,
        nip=request.nip,
        pesel=request.pesel,
        krs=request.krs,
        regon=request.regon
    )
    
    return AddressIntegrationResponse(**integration_service.to_response_dict(integration))


@app.get("/api/address-integrations/{integration_id}", response_model=AddressIntegrationResponse)
async def get_address_integration(
    integration_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Pobierz szczegóły integracji - SQLite"""
    integration = integration_service.get_integration(integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integracja nie znaleziona")
    
    return AddressIntegrationResponse(**integration_service.to_response_dict(integration))


@app.get("/api/address-integrations/{integration_id}/steps", response_model=List[AddressVerificationStep])
async def get_integration_steps(
    integration_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Pobierz kroki weryfikacji integracji - SQLite"""
    steps = integration_service.get_verification_steps(integration_id)
    if not steps:
        raise HTTPException(status_code=404, detail="Integracja nie znaleziona")
    
    return [AddressVerificationStep(**s) for s in steps]


@app.post("/api/address-integrations/{integration_id}/verify")
async def verify_integration(
    integration_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Rozpocznij weryfikację integracji - SQLite"""
    integration = integration_service.start_verification(integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integracja nie znaleziona")
    
    return {"status": "verifying", "message": "Weryfikacja rozpoczęta"}


@app.post("/api/address-integrations/{integration_id}/complete")
async def complete_integration(
    integration_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Zakończ integrację - SQLite"""
    integration = integration_service.complete_verification(integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integracja nie znaleziona")
    
    return {
        "status": "active",
        "message": "Adres e-Doręczeń został pomyślnie zintegrowany",
        "ade_address": integration.ade_address
    }


@app.delete("/api/address-integrations/{integration_id}")
async def delete_integration(
    integration_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Usuń integrację - SQLite"""
    if not integration_service.delete_integration(integration_id):
        raise HTTPException(status_code=404, detail="Integracja nie znaleziona")
    
    return {"status": "deleted", "message": "Integracja została usunięta"}


@app.get("/api/address-integrations/{integration_id}/credentials", response_model=IntegrationCredentials)
async def get_integration_credentials(
    integration_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Pobierz poświadczenia integracji - SQLite"""
    credentials = integration_service.get_credentials(integration_id)
    if not credentials:
        raise HTTPException(status_code=400, detail="Integracja nie jest aktywna lub nie istnieje")
    
    return IntegrationCredentials(**credentials)


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
        "architecture": "CQRS + Event Sourcing",
        "docs": "/docs",
        "health": "/health",
        "cqrs": {
            "events": "/api/cqrs/events",
            "stats": "/api/cqrs/stats",
            "history": "/api/cqrs/messages/{id}/history"
        }
    }

# ═══════════════════════════════════════════════════════════════
# CQRS ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/cqrs/events")
async def get_event_log(
    aggregate_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    token_data: dict = Depends(verify_jwt_token)
):
    """Pobierz log zdarzeń (Event Sourcing)"""
    query = GetEventLogQuery(
        user_id=token_data["sub"],
        aggregate_id=aggregate_id,
        event_type=event_type,
        limit=limit
    )
    result = await query_bus.dispatch(query)
    
    if result.success:
        return result.data
    raise HTTPException(status_code=400, detail=result.error)


@app.get("/api/cqrs/stats")
async def get_cqrs_stats(token_data: dict = Depends(verify_jwt_token)):
    """Pobierz statystyki CQRS/Event Store"""
    query = GetDashboardStatsQuery(user_id=token_data["sub"])
    result = await query_bus.dispatch(query)
    
    if result.success:
        return {
            **result.data,
            "event_store": event_store.get_stats()
        }
    raise HTTPException(status_code=400, detail=result.error)


@app.get("/api/cqrs/messages/{message_id}/history")
async def get_message_history(
    message_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Pobierz historię zdarzeń wiadomości (Event Sourcing)"""
    query = GetMessageHistoryQuery(
        user_id=token_data["sub"],
        message_id=message_id
    )
    result = await query_bus.dispatch(query)
    
    if result.success:
        return result.data
    raise HTTPException(status_code=404, detail=result.error)


@app.get("/api/cqrs/user/activity")
async def get_user_activity(
    limit: int = 100,
    token_data: dict = Depends(verify_jwt_token)
):
    """Pobierz aktywność użytkownika"""
    query = GetUserActivityQuery(
        user_id=token_data["sub"],
        limit=limit
    )
    result = await query_bus.dispatch(query)
    
    if result.success:
        return result.data
    raise HTTPException(status_code=400, detail=result.error)


# ═══════════════════════════════════════════════════════════════
# CQRS COMMAND ENDPOINTS (Alternative to existing endpoints)
# ═══════════════════════════════════════════════════════════════

@app.post("/api/cqrs/messages")
async def create_message_cqrs(
    message: MessageCreate,
    token_data: dict = Depends(verify_jwt_token)
):
    """Utwórz wiadomość przez CQRS Command"""
    command = CreateMessageCommand(
        user_id=token_data["sub"],
        recipient=message.recipient,
        subject=message.subject,
        content=message.content,
        attachments=message.attachments
    )
    result = await command_bus.dispatch(command)
    
    if result.success:
        return result.data
    raise HTTPException(status_code=400, detail=result.error)


@app.post("/api/cqrs/messages/{message_id}/send")
async def send_message_cqrs(
    message_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Wyślij wiadomość przez CQRS Command"""
    command = SendMessageCommand(
        user_id=token_data["sub"],
        message_id=message_id
    )
    result = await command_bus.dispatch(command)
    
    if result.success:
        return result.data
    raise HTTPException(status_code=400, detail=result.error)


@app.post("/api/cqrs/messages/{message_id}/archive")
async def archive_message_cqrs(
    message_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Zarchiwizuj wiadomość przez CQRS Command"""
    command = ArchiveMessageCommand(
        user_id=token_data["sub"],
        message_id=message_id
    )
    result = await command_bus.dispatch(command)
    
    if result.success:
        return result.data
    raise HTTPException(status_code=400, detail=result.error)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
