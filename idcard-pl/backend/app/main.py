"""
IDCard.pl - Integration Gateway API
Platforma integracji usług cyfrowych

Domeny:
- idcard.pl - ta platforma (gateway)
- szyfromat.pl - e-Doręczenia SaaS
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import httpx
import os
import uuid
import jwt
import hashlib

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

class Config:
    # IDCard.pl settings
    IDCARD_DOMAIN = os.getenv("IDCARD_DOMAIN", "idcard.pl")
    JWT_SECRET = os.getenv("JWT_SECRET", "idcard-secret-key-change-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = 24
    
    # External services - Szyfromat.pl (e-Doręczenia SaaS)
    SZYFROMAT_API_URL = os.getenv("SZYFROMAT_API_URL", "http://localhost:8500")
    SZYFROMAT_CLIENT_ID = os.getenv("SZYFROMAT_CLIENT_ID", "idcard_client")
    SZYFROMAT_CLIENT_SECRET = os.getenv("SZYFROMAT_CLIENT_SECRET", "idcard_secret")
    
    # Detax.pl (AI Asystent)
    DETAX_API_URL = os.getenv("DETAX_API_URL", "http://localhost:8000")
    
    # Przyszłe integracje
    EPUAP_API_URL = os.getenv("EPUAP_API_URL", "https://epuap.gov.pl/api")
    KSEF_API_URL = os.getenv("KSEF_API_URL", "https://ksef.mf.gov.pl/api")

config = Config()

# ═══════════════════════════════════════════════════════════════
# APP INITIALIZATION
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title="IDCard.pl - Integration Gateway",
    description="Platforma integracji usług cyfrowych - e-Doręczenia, ePUAP, KSeF",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4000",
        "http://localhost:3000",
        "https://idcard.pl",
        "https://www.idcard.pl"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

class ServiceType(str, Enum):
    EDORECZENIA = "edoreczenia"
    EPUAP = "epuap"
    KSEF = "ksef"
    MOBYWATEL = "mobywatel"
    CEPIK = "cepik"
    CEIDG = "ceidg"

class ServiceStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ERROR = "error"

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    company_name: Optional[str] = None
    nip: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    company_name: Optional[str] = None
    created_at: datetime

class ServiceConnection(BaseModel):
    """Połączenie z usługą zewnętrzną"""
    id: str
    service_type: ServiceType
    status: ServiceStatus
    external_id: Optional[str] = None
    external_address: Optional[str] = None
    connected_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    config: Dict[str, Any] = {}

class ConnectServiceRequest(BaseModel):
    """Request do połączenia z usługą"""
    service_type: ServiceType
    credentials: Dict[str, str] = {}
    config: Dict[str, Any] = {}

class UnifiedMessage(BaseModel):
    """Zunifikowana wiadomość z różnych usług"""
    id: str
    source: ServiceType
    source_id: str
    subject: str
    sender: str
    recipient: str
    received_at: datetime
    status: str
    preview: Optional[str] = None

class UnifiedNotification(BaseModel):
    """Zunifikowane powiadomienie"""
    id: str
    source: ServiceType
    type: str
    title: str
    message: str
    created_at: datetime
    read: bool = False
    action_url: Optional[str] = None

# ═══════════════════════════════════════════════════════════════
# IN-MEMORY STORAGE (produkcyjnie: baza danych)
# ═══════════════════════════════════════════════════════════════

users_db: Dict[str, Dict] = {}
connections_db: Dict[str, List[ServiceConnection]] = {}
notifications_db: Dict[str, List[UnifiedNotification]] = []

# ═══════════════════════════════════════════════════════════════
# AUTH HELPERS
# ═══════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_jwt_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=config.JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
        "iss": "idcard.pl"
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
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

# ═══════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.post("/api/auth/register")
async def register(user: UserCreate):
    """Rejestracja nowego użytkownika"""
    # Sprawdź czy email istnieje
    for u in users_db.values():
        if u["email"] == user.email:
            raise HTTPException(status_code=400, detail="Email już zarejestrowany")
    
    user_id = f"user-{uuid.uuid4().hex[:8]}"
    users_db[user_id] = {
        "id": user_id,
        "email": user.email,
        "password_hash": hash_password(user.password),
        "name": user.name,
        "company_name": user.company_name,
        "nip": user.nip,
        "created_at": datetime.utcnow()
    }
    connections_db[user_id] = []
    
    token = create_jwt_token(user_id, user.email)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user.email,
            "name": user.name
        }
    }

@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    """Logowanie użytkownika"""
    password_hash = hash_password(credentials.password)
    
    for user in users_db.values():
        if user["email"] == credentials.email and user["password_hash"] == password_hash:
            token = create_jwt_token(user["id"], user["email"])
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                    "name": user["name"]
                }
            }
    
    raise HTTPException(status_code=401, detail="Nieprawidłowy email lub hasło")

@app.get("/api/auth/me")
async def get_current_user(token_data: dict = Depends(verify_jwt_token)):
    """Pobierz dane zalogowanego użytkownika"""
    user_id = token_data["sub"]
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    
    user = users_db[user_id]
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "company_name": user.get("company_name"),
        "created_at": user["created_at"].isoformat()
    }

# ═══════════════════════════════════════════════════════════════
# SERVICES MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@app.get("/api/services")
async def list_available_services():
    """Lista dostępnych usług do integracji"""
    return {
        "services": [
            {
                "type": "edoreczenia",
                "name": "e-Doręczenia",
                "description": "Elektroniczna korespondencja urzędowa",
                "provider": "szyfromat.pl",
                "status": "available",
                "features": [
                    "Wysyłanie i odbieranie wiadomości",
                    "Potwierdzenia odbioru (UPO/UPD)",
                    "Integracja z urzędami",
                    "Archiwum wiadomości"
                ],
                "required_credentials": ["ade_address"],
                "auth_methods": ["oauth2", "mobywatel", "certificate"]
            },
            {
                "type": "epuap",
                "name": "ePUAP",
                "description": "Elektroniczna Platforma Usług Administracji Publicznej",
                "provider": "gov.pl",
                "status": "coming_soon",
                "features": [
                    "Składanie wniosków online",
                    "Profil zaufany",
                    "Skrzynka podawcza"
                ],
                "required_credentials": ["profil_zaufany"],
                "auth_methods": ["profil_zaufany", "mobywatel"]
            },
            {
                "type": "ksef",
                "name": "KSeF",
                "description": "Krajowy System e-Faktur",
                "provider": "mf.gov.pl",
                "status": "coming_soon",
                "features": [
                    "Wystawianie e-faktur",
                    "Odbieranie e-faktur",
                    "Archiwum faktur",
                    "Integracja z księgowością"
                ],
                "required_credentials": ["nip", "certificate"],
                "auth_methods": ["certificate", "token"]
            },
            {
                "type": "mobywatel",
                "name": "mObywatel",
                "description": "Cyfrowa tożsamość i dokumenty",
                "provider": "gov.pl",
                "status": "coming_soon",
                "features": [
                    "Cyfrowy dowód osobisty",
                    "Prawo jazdy",
                    "Legitymacje",
                    "Uwierzytelnianie"
                ],
                "required_credentials": [],
                "auth_methods": ["mobywatel_app"]
            },
            {
                "type": "detax",
                "name": "Detax AI",
                "description": "AI Asystent dla przedsiębiorców",
                "provider": "detax.pl",
                "status": "available",
                "features": [
                    "Czat z AI (Bielik LLM)",
                    "Moduł KSeF - e-Faktury",
                    "Moduł B2B - ocena ryzyka umów",
                    "Moduł ZUS - składki społeczne",
                    "Moduł VAT - JPK, rozliczenia"
                ],
                "required_credentials": [],
                "auth_methods": ["oauth2"]
            }
        ]
    }

@app.get("/api/services/connections")
async def list_user_connections(token_data: dict = Depends(verify_jwt_token)):
    """Lista połączeń użytkownika z usługami"""
    user_id = token_data["sub"]
    user_connections = connections_db.get(user_id, [])
    
    return {
        "connections": [
            {
                "id": conn.id,
                "service_type": conn.service_type,
                "status": conn.status,
                "external_address": conn.external_address,
                "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
                "last_sync_at": conn.last_sync_at.isoformat() if conn.last_sync_at else None
            }
            for conn in user_connections
        ]
    }

@app.post("/api/services/connect")
async def connect_service(
    request: ConnectServiceRequest,
    token_data: dict = Depends(verify_jwt_token)
):
    """Połącz z usługą zewnętrzną"""
    user_id = token_data["sub"]
    
    if user_id not in connections_db:
        connections_db[user_id] = []
    
    # Sprawdź czy już połączono
    for conn in connections_db[user_id]:
        if conn.service_type == request.service_type:
            raise HTTPException(
                status_code=400,
                detail=f"Już połączono z usługą {request.service_type}"
            )
    
    connection_id = f"conn-{uuid.uuid4().hex[:8]}"
    
    # Obsługa różnych usług
    if request.service_type == ServiceType.EDORECZENIA:
        result = await connect_edoreczenia(user_id, request, connection_id)
    elif request.service_type == ServiceType.EPUAP:
        result = await connect_epuap(user_id, request, connection_id)
    elif request.service_type == ServiceType.KSEF:
        result = await connect_ksef(user_id, request, connection_id)
    else:
        raise HTTPException(status_code=400, detail="Nieobsługiwana usługa")
    
    return result

@app.delete("/api/services/connections/{connection_id}")
async def disconnect_service(
    connection_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Rozłącz usługę"""
    user_id = token_data["sub"]
    
    if user_id not in connections_db:
        raise HTTPException(status_code=404, detail="Brak połączeń")
    
    connections_db[user_id] = [
        c for c in connections_db[user_id] if c.id != connection_id
    ]
    
    return {"status": "disconnected", "connection_id": connection_id}

# ═══════════════════════════════════════════════════════════════
# E-DORĘCZENIA INTEGRATION (szyfromat.pl)
# ═══════════════════════════════════════════════════════════════

async def connect_edoreczenia(
    user_id: str,
    request: ConnectServiceRequest,
    connection_id: str
) -> dict:
    """Połącz z e-Doręczenia przez szyfromat.pl"""
    
    ade_address = request.credentials.get("ade_address")
    if not ade_address:
        raise HTTPException(
            status_code=400,
            detail="Wymagany adres e-Doręczeń (ade_address)"
        )
    
    # Połącz z API szyfromat.pl
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Utwórz połączenie w szyfromat.pl
            response = await client.post(
                f"{config.SZYFROMAT_API_URL}/api/mailbox/connections",
                json={
                    "ade_address": ade_address,
                    "connection_method": request.config.get("auth_method", "oauth2"),
                    "mailbox_name": request.config.get("name", "IDCard Integration"),
                    "mailbox_type": request.config.get("type", "person")
                },
                headers={
                    "X-Client-ID": config.SZYFROMAT_CLIENT_ID,
                    "X-Client-Secret": config.SZYFROMAT_CLIENT_SECRET
                }
            )
            
            if response.status_code == 200:
                szyfromat_data = response.json()
                external_id = szyfromat_data.get("id")
            else:
                # Symulacja dla demo
                external_id = f"szyfromat-{uuid.uuid4().hex[:8]}"
    except Exception as e:
        # Symulacja dla demo
        external_id = f"szyfromat-{uuid.uuid4().hex[:8]}"
    
    connection = ServiceConnection(
        id=connection_id,
        service_type=ServiceType.EDORECZENIA,
        status=ServiceStatus.PENDING,
        external_id=external_id,
        external_address=ade_address,
        config=request.config
    )
    
    connections_db[user_id].append(connection)
    
    # Zwróć URL do autoryzacji
    auth_method = request.config.get("auth_method", "oauth2")
    
    return {
        "connection_id": connection_id,
        "service": "edoreczenia",
        "status": "pending",
        "external_id": external_id,
        "next_step": {
            "action": "authorize",
            "method": auth_method,
            "url": f"{config.SZYFROMAT_API_URL}/oauth/authorize?client_id={config.SZYFROMAT_CLIENT_ID}&connection_id={external_id}",
            "instructions": get_auth_instructions(auth_method)
        }
    }

def get_auth_instructions(method: str) -> List[str]:
    """Instrukcje autoryzacji dla różnych metod"""
    instructions = {
        "oauth2": [
            "Kliknij przycisk 'Autoryzuj'",
            "Zaloguj się do systemu e-Doręczeń",
            "Wyraź zgodę na dostęp aplikacji IDCard.pl",
            "Zostaniesz przekierowany z powrotem"
        ],
        "mobywatel": [
            "Otwórz aplikację mObywatel na telefonie",
            "Wybierz 'Potwierdź tożsamość'",
            "Zeskanuj kod QR lub wprowadź kod",
            "Potwierdź swoją tożsamość"
        ],
        "certificate": [
            "Przygotuj certyfikat kwalifikowany (.p12/.pfx)",
            "Kliknij 'Wybierz certyfikat'",
            "Wprowadź hasło do certyfikatu",
            "Poczekaj na weryfikację"
        ]
    }
    return instructions.get(method, ["Postępuj zgodnie z instrukcjami"])

@app.post("/api/services/edoreczenia/authorize/callback")
async def edoreczenia_auth_callback(
    connection_id: str,
    code: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Callback autoryzacji e-Doręczeń"""
    user_id = token_data["sub"]
    
    # Znajdź połączenie
    for conn in connections_db.get(user_id, []):
        if conn.id == connection_id:
            conn.status = ServiceStatus.ACTIVE
            conn.connected_at = datetime.utcnow()
            
            # Dodaj powiadomienie
            add_notification(
                user_id,
                ServiceType.EDORECZENIA,
                "connection",
                "e-Doręczenia połączone",
                f"Pomyślnie połączono skrzynkę {conn.external_address}",
                f"/services/edoreczenia/{connection_id}"
            )
            
            return {
                "status": "connected",
                "connection_id": connection_id,
                "message": "Pomyślnie połączono z e-Doręczenia"
            }
    
    raise HTTPException(status_code=404, detail="Połączenie nie znalezione")

@app.get("/api/services/edoreczenia/messages")
async def get_edoreczenia_messages(
    folder: str = "inbox",
    limit: int = 20,
    token_data: dict = Depends(verify_jwt_token)
):
    """Pobierz wiadomości z e-Doręczeń przez szyfromat.pl"""
    user_id = token_data["sub"]
    
    # Znajdź aktywne połączenie
    connection = None
    for conn in connections_db.get(user_id, []):
        if conn.service_type == ServiceType.EDORECZENIA and conn.status == ServiceStatus.ACTIVE:
            connection = conn
            break
    
    if not connection:
        raise HTTPException(status_code=400, detail="Brak aktywnego połączenia z e-Doręczenia")
    
    # Pobierz wiadomości z szyfromat.pl
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{config.SZYFROMAT_API_URL}/api/messages",
                params={"folder": folder, "limit": limit},
                headers={
                    "X-Client-ID": config.SZYFROMAT_CLIENT_ID,
                    "X-Connection-ID": connection.external_id
                }
            )
            
            if response.status_code == 200:
                messages = response.json()
                # Konwertuj na zunifikowany format
                return {
                    "messages": [
                        UnifiedMessage(
                            id=f"edor-{msg['id']}",
                            source=ServiceType.EDORECZENIA,
                            source_id=msg["id"],
                            subject=msg.get("subject", ""),
                            sender=msg.get("sender", {}).get("address", ""),
                            recipient=msg.get("recipient", {}).get("address", ""),
                            received_at=datetime.fromisoformat(msg["receivedAt"]) if msg.get("receivedAt") else datetime.utcnow(),
                            status=msg.get("status", ""),
                            preview=msg.get("content", "")[:100] if msg.get("content") else None
                        ).dict()
                        for msg in messages
                    ],
                    "source": "szyfromat.pl",
                    "folder": folder
                }
    except Exception as e:
        pass
    
    # Demo data
    return {
        "messages": [
            {
                "id": "edor-demo-001",
                "source": "edoreczenia",
                "source_id": "msg-demo-001",
                "subject": "Zawiadomienie o wszczęciu postępowania",
                "sender": "AE:PL-URZAD-SKAR-BOWY-01",
                "recipient": connection.external_address,
                "received_at": datetime.utcnow().isoformat(),
                "status": "RECEIVED",
                "preview": "Na podstawie art. 165 § 1 Ordynacji podatkowej..."
            }
        ],
        "source": "szyfromat.pl (demo)",
        "folder": folder
    }

@app.post("/api/services/edoreczenia/messages")
async def send_edoreczenia_message(
    recipient: str,
    subject: str,
    content: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Wyślij wiadomość przez e-Doręczenia"""
    user_id = token_data["sub"]
    
    # Znajdź aktywne połączenie
    connection = None
    for conn in connections_db.get(user_id, []):
        if conn.service_type == ServiceType.EDORECZENIA and conn.status == ServiceStatus.ACTIVE:
            connection = conn
            break
    
    if not connection:
        raise HTTPException(status_code=400, detail="Brak aktywnego połączenia z e-Doręczenia")
    
    # Wyślij przez szyfromat.pl
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{config.SZYFROMAT_API_URL}/api/messages",
                json={
                    "recipient": recipient,
                    "subject": subject,
                    "content": content
                },
                headers={
                    "X-Client-ID": config.SZYFROMAT_CLIENT_ID,
                    "X-Connection-ID": connection.external_id
                }
            )
            
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    
    # Demo response
    return {
        "id": f"msg-{uuid.uuid4().hex[:8]}",
        "status": "SENT",
        "subject": subject,
        "recipient": recipient,
        "sent_at": datetime.utcnow().isoformat()
    }

# ═══════════════════════════════════════════════════════════════
# ePUAP INTEGRATION (placeholder)
# ═══════════════════════════════════════════════════════════════

async def connect_epuap(
    user_id: str,
    request: ConnectServiceRequest,
    connection_id: str
) -> dict:
    """Połącz z ePUAP"""
    raise HTTPException(
        status_code=501,
        detail="Integracja z ePUAP będzie dostępna wkrótce"
    )

# ═══════════════════════════════════════════════════════════════
# KSeF INTEGRATION (placeholder)
# ═══════════════════════════════════════════════════════════════

async def connect_ksef(
    user_id: str,
    request: ConnectServiceRequest,
    connection_id: str
) -> dict:
    """Połącz z KSeF"""
    raise HTTPException(
        status_code=501,
        detail="Integracja z KSeF będzie dostępna wkrótce"
    )

# ═══════════════════════════════════════════════════════════════
# UNIFIED DASHBOARD
# ═══════════════════════════════════════════════════════════════

@app.get("/api/dashboard")
async def get_dashboard(token_data: dict = Depends(verify_jwt_token)):
    """Zunifikowany dashboard - wszystkie usługi w jednym miejscu"""
    user_id = token_data["sub"]
    user_connections = connections_db.get(user_id, [])
    
    # Zbierz statystyki z wszystkich usług
    stats = {
        "total_connections": len(user_connections),
        "active_connections": len([c for c in user_connections if c.status == ServiceStatus.ACTIVE]),
        "services": {}
    }
    
    for conn in user_connections:
        if conn.service_type == ServiceType.EDORECZENIA:
            stats["services"]["edoreczenia"] = {
                "status": conn.status,
                "address": conn.external_address,
                "unread_messages": 3,  # Demo
                "last_sync": conn.last_sync_at.isoformat() if conn.last_sync_at else None
            }
    
    return {
        "user": users_db.get(user_id, {}),
        "stats": stats,
        "recent_activity": [
            {
                "type": "message_received",
                "service": "edoreczenia",
                "title": "Nowa wiadomość z Urzędu Skarbowego",
                "time": datetime.utcnow().isoformat()
            }
        ],
        "notifications": get_user_notifications(user_id)
    }

@app.get("/api/dashboard/unified-inbox")
async def get_unified_inbox(
    limit: int = 50,
    token_data: dict = Depends(verify_jwt_token)
):
    """Zunifikowana skrzynka odbiorcza - wiadomości ze wszystkich usług"""
    user_id = token_data["sub"]
    
    all_messages = []
    
    # Pobierz wiadomości z każdej aktywnej usługi
    for conn in connections_db.get(user_id, []):
        if conn.status != ServiceStatus.ACTIVE:
            continue
        
        if conn.service_type == ServiceType.EDORECZENIA:
            # Demo messages
            all_messages.append({
                "id": "unified-edor-001",
                "source": "edoreczenia",
                "source_icon": "📧",
                "subject": "Zawiadomienie o wszczęciu postępowania",
                "sender": "Urząd Skarbowy",
                "sender_address": "AE:PL-URZAD-SKAR-BOWY-01",
                "received_at": datetime.utcnow().isoformat(),
                "status": "unread",
                "preview": "Na podstawie art. 165 § 1..."
            })
    
    # Sortuj po dacie
    all_messages.sort(key=lambda x: x["received_at"], reverse=True)
    
    return {
        "messages": all_messages[:limit],
        "total": len(all_messages)
    }

# ═══════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════

def add_notification(
    user_id: str,
    source: ServiceType,
    type: str,
    title: str,
    message: str,
    action_url: str = None
):
    """Dodaj powiadomienie"""
    if user_id not in notifications_db:
        notifications_db[user_id] = []
    
    notifications_db[user_id].append(UnifiedNotification(
        id=f"notif-{uuid.uuid4().hex[:8]}",
        source=source,
        type=type,
        title=title,
        message=message,
        created_at=datetime.utcnow(),
        action_url=action_url
    ))

def get_user_notifications(user_id: str, unread_only: bool = False) -> List[dict]:
    """Pobierz powiadomienia użytkownika"""
    notifications = notifications_db.get(user_id, [])
    if unread_only:
        notifications = [n for n in notifications if not n.read]
    return [n.dict() for n in notifications[-10:]]

@app.get("/api/notifications")
async def get_notifications(
    unread_only: bool = False,
    token_data: dict = Depends(verify_jwt_token)
):
    """Pobierz powiadomienia"""
    user_id = token_data["sub"]
    return {
        "notifications": get_user_notifications(user_id, unread_only)
    }

@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Oznacz powiadomienie jako przeczytane"""
    user_id = token_data["sub"]
    
    for notif in notifications_db.get(user_id, []):
        if notif.id == notification_id:
            notif.read = True
            return {"status": "ok"}
    
    raise HTTPException(status_code=404, detail="Powiadomienie nie znalezione")

# ═══════════════════════════════════════════════════════════════
# HEALTH & INFO
# ═══════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "IDCard.pl Integration Gateway",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "IDCard.pl - Integration Gateway",
        "version": "1.0.0",
        "description": "Platforma integracji usług cyfrowych",
        "domains": {
            "gateway": "idcard.pl",
            "edoreczenia": "szyfromat.pl"
        },
        "docs": "/docs",
        "services": "/api/services"
    }

# ═══════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4000)
