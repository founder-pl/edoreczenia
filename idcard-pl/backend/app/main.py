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
    
    # Demo user (development)
    DEMO_USER_EMAIL = os.getenv("DEMO_USER_EMAIL", "demo@idcard.pl")
    DEMO_USER_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "demo123")
    DEMO_USER_NAME = os.getenv("DEMO_USER_NAME", "Demo User")
    DEMO_USER_COMPANY = os.getenv("DEMO_USER_COMPANY", "Demo Company Sp. z o.o.")
    
    # External services - Szyfromat.pl (e-Doręczenia SaaS)
    SZYFROMAT_API_URL = os.getenv("SZYFROMAT_API_URL", "http://localhost:8500")
    SZYFROMAT_CLIENT_ID = os.getenv("SZYFROMAT_CLIENT_ID", "idcard_client")
    SZYFROMAT_CLIENT_SECRET = os.getenv("SZYFROMAT_CLIENT_SECRET", "idcard_secret")
    
    # Detax.pl (AI Asystent)
    DETAX_API_URL = os.getenv("DETAX_API_URL", "http://localhost:8005")
    
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
    DETAX = "detax"
    EPUAP = "epuap"
    KSEF = "ksef"
    MOBYWATEL = "mobywatel"
    CEPIK = "cepik"
    CEIDG = "ceidg"

class IdentityType(str, Enum):
    """Typ tożsamości w wallet"""
    PERSONAL = "personal"       # Osoba fizyczna
    COMPANY = "company"         # Firma
    EMPLOYEE = "employee"       # Pracownik firmy
    FAMILY = "family"           # Członek rodziny
    CHILD = "child"             # Dziecko (opiekun)
    REPRESENTATIVE = "representative"  # Pełnomocnik

class AuthorizationType(str, Enum):
    """Typ upoważnienia"""
    FULL = "full"                       # Pełne pełnomocnictwo
    ACCOUNTING = "accounting"           # Księgowość (ZUS, US, e-Faktury)
    LEGAL = "legal"                     # Prawne (sądy, urzędy)
    TAX = "tax"                         # Podatkowe (US, KSeF)
    HR = "hr"                           # Kadry (ZUS, PIP)
    EDORECZENIA = "edoreczenia"         # Tylko e-Doręczenia
    EPUAP = "epuap"                     # Tylko ePUAP
    KSEF = "ksef"                       # Tylko KSeF
    READ_ONLY = "read_only"             # Tylko odczyt
    CUSTOM = "custom"                   # Własne uprawnienia

class AuthorizationStatus(str, Enum):
    """Status upoważnienia"""
    PENDING = "pending"           # Oczekuje na akceptację
    ACTIVE = "active"             # Aktywne
    EXPIRED = "expired"           # Wygasłe
    REVOKED = "revoked"           # Odwołane
    REJECTED = "rejected"         # Odrzucone

class Authorization(BaseModel):
    """Upoważnienie do działania w imieniu innej tożsamości"""
    id: str
    
    # Kto upoważnia (mocodawca)
    grantor_user_id: str          # ID użytkownika upoważniającego
    grantor_identity_id: str      # ID tożsamości upoważniającej
    grantor_name: str             # Nazwa mocodawcy (do wyświetlenia)
    
    # Kto jest upoważniony (pełnomocnik)
    grantee_user_id: str          # ID użytkownika upoważnionego
    grantee_email: str            # Email pełnomocnika
    grantee_name: Optional[str] = None
    
    # Szczegóły upoważnienia
    type: AuthorizationType
    title: str                    # np. "Pełnomocnictwo do spraw księgowych"
    description: Optional[str] = None
    
    # Zakres uprawnień
    permissions: List[str] = []   # Lista konkretnych uprawnień
    services: List[str] = []      # Lista usług (edoreczenia, ksef, epuap)
    
    # Ważność
    valid_from: datetime
    valid_until: Optional[datetime] = None  # None = bezterminowe
    
    # Status
    status: AuthorizationStatus = AuthorizationStatus.PENDING
    
    # Metadane
    created_at: datetime
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None
    
    # Dokument pełnomocnictwa (opcjonalny)
    document_id: Optional[str] = None
    document_url: Optional[str] = None

class Identity(BaseModel):
    """Tożsamość w wallet IDCard.pl"""
    id: str
    type: IdentityType
    name: str                   # Imię i nazwisko / Nazwa firmy
    country: str = "PL"         # Kod kraju
    
    # Identyfikatory (opcjonalne, zależne od typu)
    pesel: Optional[str] = None
    nip: Optional[str] = None
    krs: Optional[str] = None
    regon: Optional[str] = None
    
    # Adresy usług
    ade_address: Optional[str] = None  # e-Doręczenia (AE:PL-...)
    epuap_address: Optional[str] = None  # ePUAP
    
    # Metadane
    is_default: bool = False
    is_verified: bool = False
    created_at: datetime = None
    
    # Relacja (dla pracowników, rodziny)
    parent_identity_id: Optional[str] = None
    role: Optional[str] = None  # np. "właściciel", "księgowy", "dziecko"

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
    krs: Optional[str] = None
    ade_address: Optional[str] = None  # Adres e-Doręczeń (AE:PL-...)

class UserLogin(BaseModel):
    email: str
    password: str

class EmailAlias(BaseModel):
    """Alias email w domenie @idcard.pl"""
    alias: str  # np. nip-1234567890@idcard.pl
    alias_type: str  # nip, krs, ade, company
    target_email: str  # docelowy email użytkownika
    active: bool = True

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    company_name: Optional[str] = None
    nip: Optional[str] = None
    krs: Optional[str] = None
    ade_address: Optional[str] = None
    email_aliases: List[str] = []  # Lista aliasów @idcard.pl
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
notifications_db: Dict[str, List[UnifiedNotification]] = {}
email_aliases_db: Dict[str, EmailAlias] = {}  # alias -> EmailAlias
identities_db: Dict[str, List[Identity]] = {}  # user_id -> List[Identity]
authorizations_db: Dict[str, Authorization] = {}  # auth_id -> Authorization
user_authorizations_granted: Dict[str, List[str]] = {}  # user_id -> List[auth_id] (udzielone)
user_authorizations_received: Dict[str, List[str]] = {}  # user_id -> List[auth_id] (otrzymane)

def generate_email_aliases(user_id: str, email: str, nip: str = None, krs: str = None, 
                           ade_address: str = None, company_name: str = None) -> List[str]:
    """
    Generuje aliasy email w domenie @idcard.pl dla identyfikatorów firmy.
    Każdy alias przekierowuje na główny email użytkownika.
    """
    aliases = []
    
    # Alias dla NIP: nip-1234567890@idcard.pl
    if nip:
        nip_clean = nip.replace("-", "").replace(" ", "")
        alias = f"nip-{nip_clean}@idcard.pl"
        email_aliases_db[alias] = EmailAlias(
            alias=alias,
            alias_type="nip",
            target_email=email,
            active=True
        )
        aliases.append(alias)
    
    # Alias dla KRS: krs-0000123456@idcard.pl
    if krs:
        krs_clean = krs.replace(" ", "")
        alias = f"krs-{krs_clean}@idcard.pl"
        email_aliases_db[alias] = EmailAlias(
            alias=alias,
            alias_type="krs",
            target_email=email,
            active=True
        )
        aliases.append(alias)
    
    # Alias dla adresu e-Doręczeń: ae-pl-kowalski-12345@idcard.pl
    if ade_address:
        # AE:PL-KOWALSKI-96046-01 -> ae-pl-kowalski-96046-01
        ade_clean = ade_address.lower().replace(":", "-").replace(" ", "")
        alias = f"{ade_clean}@idcard.pl"
        email_aliases_db[alias] = EmailAlias(
            alias=alias,
            alias_type="ade",
            target_email=email,
            active=True
        )
        aliases.append(alias)
    
    # Alias dla nazwy firmy: firma-nazwa@idcard.pl
    if company_name:
        # "Kowalski Sp. z o.o." -> "kowalski-sp-z-oo"
        import re
        company_clean = company_name.lower()
        company_clean = re.sub(r'[^a-z0-9]+', '-', company_clean)
        company_clean = company_clean.strip('-')
        if company_clean:
            alias = f"firma-{company_clean}@idcard.pl"
            email_aliases_db[alias] = EmailAlias(
                alias=alias,
                alias_type="company",
                target_email=email,
                active=True
            )
            aliases.append(alias)
    
    return aliases

# Inicjalizacja demo użytkownika
def init_demo_user():
    demo_id = "user-demo"
    demo_password_hash = hashlib.sha256(config.DEMO_USER_PASSWORD.encode()).hexdigest()
    
    # Generuj aliasy dla demo użytkownika
    demo_aliases = generate_email_aliases(
        user_id=demo_id,
        email=config.DEMO_USER_EMAIL,
        nip="1234567890",
        krs="0000123456",
        ade_address="AE:PL-DEMO-USER-1234-01",
        company_name=config.DEMO_USER_COMPANY
    )
    
    users_db[demo_id] = {
        "id": demo_id,
        "email": config.DEMO_USER_EMAIL,
        "password_hash": demo_password_hash,
        "name": config.DEMO_USER_NAME,
        "company_name": config.DEMO_USER_COMPANY,
        "nip": "1234567890",
        "krs": "0000123456",
        "ade_address": "AE:PL-DEMO-USER-1234-01",
        "email_aliases": demo_aliases,
        "created_at": datetime.utcnow()
    }
    connections_db[demo_id] = []

init_demo_user()

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
    """
    Rejestracja nowego użytkownika.
    
    Automatycznie tworzy aliasy email w domenie @idcard.pl dla:
    - NIP: nip-1234567890@idcard.pl
    - KRS: krs-0000123456@idcard.pl  
    - Adres e-Doręczeń: ae-pl-nazwa-12345@idcard.pl
    - Nazwa firmy: firma-nazwa@idcard.pl
    
    Każdy alias przekierowuje na główny email użytkownika.
    """
    # Sprawdź czy email istnieje
    for u in users_db.values():
        if u["email"] == user.email:
            raise HTTPException(status_code=400, detail="Email już zarejestrowany")
    
    user_id = f"user-{uuid.uuid4().hex[:8]}"
    
    # Generuj aliasy email @idcard.pl
    email_aliases = generate_email_aliases(
        user_id=user_id,
        email=user.email,
        nip=user.nip,
        krs=user.krs,
        ade_address=user.ade_address,
        company_name=user.company_name
    )
    
    users_db[user_id] = {
        "id": user_id,
        "email": user.email,
        "password_hash": hash_password(user.password),
        "name": user.name,
        "company_name": user.company_name,
        "nip": user.nip,
        "krs": user.krs,
        "ade_address": user.ade_address,
        "email_aliases": email_aliases,
        "created_at": datetime.utcnow(),
        # Automatyczna autoryzacja do wszystkich usług
        "authorized_services": ["szyfromat", "detax", "nextcloud"],
        # Trial Detax.pl - 3 darmowe zapytania
        "detax_trial": {
            "queries_remaining": 3,
            "queries_used": 0,
            "trial_started": datetime.utcnow().isoformat(),
            "subscription_required": False
        }
    }
    connections_db[user_id] = []
    
    token = create_jwt_token(user_id, user.email)
    
    # Automatyczne połączenia z usługami
    auto_connections = []
    for service in ["szyfromat", "detax", "nextcloud"]:
        conn_id = f"conn-{uuid.uuid4().hex[:8]}"
        connection = ServiceConnection(
            id=conn_id,
            service_type=ServiceType.EDORECZENIA if service == "szyfromat" else ServiceType.KSEF,
            status=ServiceStatus.ACTIVE,
            external_id=f"{service}-{uuid.uuid4().hex[:8]}",
            connected_at=datetime.utcnow()
        )
        connections_db[user_id].append(connection)
        auto_connections.append({"service": service, "status": "active"})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user.email,
            "name": user.name,
            "email_aliases": email_aliases,
            "authorized_services": ["szyfromat", "detax", "nextcloud"]
        },
        "auto_connections": auto_connections,
        "detax_trial": {
            "queries_remaining": 3,
            "message": "Masz 3 darmowe zapytania do AI Detax.pl!"
        },
        "message": f"Konto utworzone! Masz dostęp do wszystkich usług."
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
        "nip": user.get("nip"),
        "krs": user.get("krs"),
        "ade_address": user.get("ade_address"),
        "email_aliases": user.get("email_aliases", []),
        "created_at": user["created_at"].isoformat()
    }

# ═══════════════════════════════════════════════════════════════
# EMAIL ALIASES
# ═══════════════════════════════════════════════════════════════

@app.get("/api/aliases")
async def get_my_aliases(token_data: dict = Depends(verify_jwt_token)):
    """Pobierz aliasy email zalogowanego użytkownika"""
    user_id = token_data["sub"]
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    
    user = users_db[user_id]
    aliases = user.get("email_aliases", [])
    
    # Pobierz szczegóły aliasów
    alias_details = []
    for alias in aliases:
        if alias in email_aliases_db:
            alias_details.append(email_aliases_db[alias].dict())
    
    return {
        "aliases": alias_details,
        "count": len(alias_details),
        "info": "Każdy alias przekierowuje emaile na Twój główny adres"
    }

@app.get("/api/aliases/lookup/{alias}")
async def lookup_alias(alias: str):
    """
    Wyszukaj użytkownika po aliasie email @idcard.pl.
    Pozwala na korespondencję używając NIP, KRS, adresu ADE lub nazwy firmy.
    """
    # Dodaj domenę jeśli nie ma
    if "@" not in alias:
        alias = f"{alias}@idcard.pl"
    
    if alias not in email_aliases_db:
        raise HTTPException(status_code=404, detail="Alias nie znaleziony")
    
    alias_data = email_aliases_db[alias]
    
    return {
        "alias": alias,
        "alias_type": alias_data.alias_type,
        "active": alias_data.active,
        "can_receive_email": alias_data.active,
        "info": f"Wiadomości wysłane na {alias} zostaną dostarczone do właściciela"
    }

@app.post("/api/aliases/add")
async def add_alias(
    alias_type: str,
    value: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Dodaj nowy alias email dla użytkownika.
    
    alias_type: nip, krs, ade, company
    value: wartość identyfikatora (np. NIP, KRS, adres ADE)
    """
    user_id = token_data["sub"]
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    
    user = users_db[user_id]
    email = user["email"]
    
    # Generuj alias w zależności od typu
    if alias_type == "nip":
        new_aliases = generate_email_aliases(user_id, email, nip=value)
    elif alias_type == "krs":
        new_aliases = generate_email_aliases(user_id, email, krs=value)
    elif alias_type == "ade":
        new_aliases = generate_email_aliases(user_id, email, ade_address=value)
    elif alias_type == "company":
        new_aliases = generate_email_aliases(user_id, email, company_name=value)
    else:
        raise HTTPException(status_code=400, detail="Nieznany typ aliasu")
    
    # Dodaj do użytkownika
    existing_aliases = user.get("email_aliases", [])
    user["email_aliases"] = list(set(existing_aliases + new_aliases))
    
    return {
        "added": new_aliases,
        "all_aliases": user["email_aliases"],
        "message": f"Dodano alias: {new_aliases[0] if new_aliases else 'brak'}"
    }

# ═══════════════════════════════════════════════════════════════
# DETAX TRIAL MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@app.get("/api/detax/trial")
async def get_detax_trial(token_data: dict = Depends(verify_jwt_token)):
    """Sprawdź status trialu Detax.pl"""
    user_id = token_data["sub"]
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    
    user = users_db[user_id]
    trial = user.get("detax_trial", {
        "queries_remaining": 0,
        "queries_used": 0,
        "subscription_required": True
    })
    
    return {
        "trial_active": trial.get("queries_remaining", 0) > 0,
        "queries_remaining": trial.get("queries_remaining", 0),
        "queries_used": trial.get("queries_used", 0),
        "subscription_required": trial.get("subscription_required", True),
        "subscription_url": "http://localhost:5001/api/shop/plans" if trial.get("subscription_required") else None
    }

@app.post("/api/detax/use-query")
async def use_detax_query(token_data: dict = Depends(verify_jwt_token)):
    """
    Użyj jednego zapytania z trialu Detax.pl.
    
    Zwraca:
    - allowed: True jeśli można zadać pytanie
    - queries_remaining: ile zostało zapytań
    - subscription_required: True jeśli trial wyczerpany
    """
    user_id = token_data["sub"]
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    
    user = users_db[user_id]
    
    # Sprawdź czy ma aktywną subskrypcję
    if user.get("detax_subscription_active"):
        return {
            "allowed": True,
            "queries_remaining": "unlimited",
            "subscription_active": True
        }
    
    # Sprawdź trial
    trial = user.get("detax_trial", {"queries_remaining": 0, "queries_used": 0})
    
    if trial.get("queries_remaining", 0) <= 0:
        return {
            "allowed": False,
            "queries_remaining": 0,
            "subscription_required": True,
            "message": "Trial wyczerpany. Kup subskrypcję aby kontynuować.",
            "subscription_url": "http://localhost:5001/api/shop/plans"
        }
    
    # Użyj zapytania
    trial["queries_remaining"] -= 1
    trial["queries_used"] += 1
    
    if trial["queries_remaining"] <= 0:
        trial["subscription_required"] = True
    
    user["detax_trial"] = trial
    
    return {
        "allowed": True,
        "queries_remaining": trial["queries_remaining"],
        "queries_used": trial["queries_used"],
        "subscription_required": trial.get("subscription_required", False),
        "message": f"Pozostało {trial['queries_remaining']} darmowych zapytań" if trial["queries_remaining"] > 0 else "To było ostatnie darmowe zapytanie!"
    }

@app.post("/api/detax/activate-subscription")
async def activate_detax_subscription(
    subscription_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Aktywuj subskrypcję Detax.pl po płatności"""
    user_id = token_data["sub"]
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    
    user = users_db[user_id]
    user["detax_subscription_active"] = True
    user["detax_subscription_id"] = subscription_id
    user["detax_subscription_activated"] = datetime.utcnow().isoformat()
    
    # Wyłącz trial
    if "detax_trial" in user:
        user["detax_trial"]["subscription_required"] = False
    
    return {
        "status": "active",
        "subscription_id": subscription_id,
        "message": "Subskrypcja Detax.pl aktywna! Nielimitowane zapytania."
    }

# ═══════════════════════════════════════════════════════════════
# IDENTITY WALLET - Zarządzanie tożsamościami
# ═══════════════════════════════════════════════════════════════

class CreateIdentityRequest(BaseModel):
    type: IdentityType
    name: str
    country: str = "PL"
    pesel: Optional[str] = None
    nip: Optional[str] = None
    krs: Optional[str] = None
    regon: Optional[str] = None
    ade_address: Optional[str] = None
    epuap_address: Optional[str] = None
    role: Optional[str] = None
    parent_identity_id: Optional[str] = None

@app.get("/api/identities")
async def list_identities(token_data: dict = Depends(verify_jwt_token)):
    """Lista tożsamości użytkownika (wallet)"""
    user_id = token_data["sub"]
    identities = identities_db.get(user_id, [])
    
    # Jeśli brak tożsamości, utwórz domyślną z danych użytkownika
    if not identities and user_id in users_db:
        user = users_db[user_id]
        default_identity = Identity(
            id=f"id-{uuid.uuid4().hex[:8]}",
            type=IdentityType.PERSONAL,
            name=user.get("name", "Użytkownik"),
            country="PL",
            nip=user.get("nip"),
            krs=user.get("krs"),
            ade_address=user.get("ade_address"),
            is_default=True,
            is_verified=False,
            created_at=datetime.utcnow()
        )
        identities_db[user_id] = [default_identity]
        identities = [default_identity]
    
    return {
        "identities": [i.dict() for i in identities],
        "default_identity_id": next((i.id for i in identities if i.is_default), None)
    }

@app.post("/api/identities")
async def create_identity(
    request: CreateIdentityRequest,
    token_data: dict = Depends(verify_jwt_token)
):
    """Dodaj nową tożsamość do wallet"""
    user_id = token_data["sub"]
    
    identity = Identity(
        id=f"id-{uuid.uuid4().hex[:8]}",
        type=request.type,
        name=request.name,
        country=request.country,
        pesel=request.pesel,
        nip=request.nip,
        krs=request.krs,
        regon=request.regon,
        ade_address=request.ade_address,
        epuap_address=request.epuap_address,
        role=request.role,
        parent_identity_id=request.parent_identity_id,
        is_default=len(identities_db.get(user_id, [])) == 0,
        is_verified=False,
        created_at=datetime.utcnow()
    )
    
    if user_id not in identities_db:
        identities_db[user_id] = []
    identities_db[user_id].append(identity)
    
    return {"identity": identity.dict(), "message": "Tożsamość dodana do wallet"}

@app.put("/api/identities/{identity_id}")
async def update_identity(
    identity_id: str,
    request: CreateIdentityRequest,
    token_data: dict = Depends(verify_jwt_token)
):
    """Aktualizuj tożsamość"""
    user_id = token_data["sub"]
    
    for i, identity in enumerate(identities_db.get(user_id, [])):
        if identity.id == identity_id:
            identities_db[user_id][i] = Identity(
                id=identity_id,
                type=request.type,
                name=request.name,
                country=request.country,
                pesel=request.pesel,
                nip=request.nip,
                krs=request.krs,
                regon=request.regon,
                ade_address=request.ade_address,
                epuap_address=request.epuap_address,
                role=request.role,
                parent_identity_id=request.parent_identity_id,
                is_default=identity.is_default,
                is_verified=identity.is_verified,
                created_at=identity.created_at
            )
            return {"identity": identities_db[user_id][i].dict()}
    
    raise HTTPException(status_code=404, detail="Tożsamość nie znaleziona")

@app.delete("/api/identities/{identity_id}")
async def delete_identity(
    identity_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Usuń tożsamość z wallet"""
    user_id = token_data["sub"]
    
    identities = identities_db.get(user_id, [])
    for i, identity in enumerate(identities):
        if identity.id == identity_id:
            if identity.is_default and len(identities) > 1:
                raise HTTPException(status_code=400, detail="Nie można usunąć domyślnej tożsamości")
            identities_db[user_id].pop(i)
            return {"message": "Tożsamość usunięta"}
    
    raise HTTPException(status_code=404, detail="Tożsamość nie znaleziona")

@app.post("/api/identities/{identity_id}/set-default")
async def set_default_identity(
    identity_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Ustaw tożsamość jako domyślną"""
    user_id = token_data["sub"]
    
    found = False
    for identity in identities_db.get(user_id, []):
        if identity.id == identity_id:
            identity.is_default = True
            found = True
        else:
            identity.is_default = False
    
    if not found:
        raise HTTPException(status_code=404, detail="Tożsamość nie znaleziona")
    
    return {"message": "Domyślna tożsamość zmieniona"}

@app.get("/api/identities/{identity_id}/ade-address")
async def get_identity_ade_address(
    identity_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Pobierz adres e-Doręczeń dla tożsamości"""
    user_id = token_data["sub"]
    
    for identity in identities_db.get(user_id, []):
        if identity.id == identity_id:
            if identity.ade_address:
                return {"ade_address": identity.ade_address}
            else:
                return {"ade_address": None, "message": "Brak adresu e-Doręczeń dla tej tożsamości"}
    
    raise HTTPException(status_code=404, detail="Tożsamość nie znaleziona")

# ═══════════════════════════════════════════════════════════════
# AUTHORIZATIONS - Upoważnienia i pełnomocnictwa
# ═══════════════════════════════════════════════════════════════

class CreateAuthorizationRequest(BaseModel):
    """Request do utworzenia upoważnienia"""
    identity_id: str              # Tożsamość upoważniająca
    grantee_email: str            # Email pełnomocnika
    type: AuthorizationType
    title: str
    description: Optional[str] = None
    permissions: List[str] = []
    services: List[str] = []      # np. ["edoreczenia", "ksef"]
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

# Predefiniowane zestawy uprawnień
AUTHORIZATION_PRESETS = {
    AuthorizationType.FULL: {
        "permissions": ["read", "write", "send", "sign", "manage"],
        "services": ["edoreczenia", "epuap", "ksef", "detax"]
    },
    AuthorizationType.ACCOUNTING: {
        "permissions": ["read", "write", "send"],
        "services": ["edoreczenia", "ksef", "detax"]
    },
    AuthorizationType.LEGAL: {
        "permissions": ["read", "write", "send", "sign"],
        "services": ["edoreczenia", "epuap"]
    },
    AuthorizationType.TAX: {
        "permissions": ["read", "write", "send"],
        "services": ["ksef", "detax"]
    },
    AuthorizationType.HR: {
        "permissions": ["read", "write", "send"],
        "services": ["edoreczenia", "epuap"]
    },
    AuthorizationType.EDORECZENIA: {
        "permissions": ["read", "write", "send"],
        "services": ["edoreczenia"]
    },
    AuthorizationType.KSEF: {
        "permissions": ["read", "write", "send"],
        "services": ["ksef"]
    },
    AuthorizationType.READ_ONLY: {
        "permissions": ["read"],
        "services": ["edoreczenia", "epuap", "ksef", "detax"]
    }
}

@app.get("/api/authorizations")
async def list_authorizations(token_data: dict = Depends(verify_jwt_token)):
    """Lista upoważnień użytkownika (udzielonych i otrzymanych)"""
    user_id = token_data["sub"]
    
    # Upoważnienia udzielone przez użytkownika
    granted_ids = user_authorizations_granted.get(user_id, [])
    granted = [authorizations_db[aid].dict() for aid in granted_ids if aid in authorizations_db]
    
    # Upoważnienia otrzymane przez użytkownika
    received_ids = user_authorizations_received.get(user_id, [])
    received = [authorizations_db[aid].dict() for aid in received_ids if aid in authorizations_db]
    
    return {
        "granted": granted,      # Udzielone innym
        "received": received,    # Otrzymane od innych
        "total_granted": len(granted),
        "total_received": len(received),
        "active_received": len([a for a in received if a["status"] == "active"])
    }

@app.post("/api/authorizations")
async def create_authorization(
    request: CreateAuthorizationRequest,
    token_data: dict = Depends(verify_jwt_token)
):
    """Utwórz nowe upoważnienie (pełnomocnictwo)"""
    user_id = token_data["sub"]
    
    # Sprawdź czy tożsamość należy do użytkownika
    identity = None
    for i in identities_db.get(user_id, []):
        if i.id == request.identity_id:
            identity = i
            break
    
    if not identity:
        raise HTTPException(status_code=404, detail="Tożsamość nie znaleziona")
    
    # Znajdź użytkownika po email (pełnomocnika)
    grantee_user_id = None
    grantee_name = None
    for uid, user in users_db.items():
        if user.get("email") == request.grantee_email:
            grantee_user_id = uid
            grantee_name = user.get("name")
            break
    
    # Użyj predefiniowanych uprawnień jeśli nie podano
    preset = AUTHORIZATION_PRESETS.get(request.type, {})
    permissions = request.permissions or preset.get("permissions", [])
    services = request.services or preset.get("services", [])
    
    auth_id = f"auth-{uuid.uuid4().hex[:8]}"
    authorization = Authorization(
        id=auth_id,
        grantor_user_id=user_id,
        grantor_identity_id=request.identity_id,
        grantor_name=identity.name,
        grantee_user_id=grantee_user_id or f"pending-{request.grantee_email}",
        grantee_email=request.grantee_email,
        grantee_name=grantee_name,
        type=request.type,
        title=request.title,
        description=request.description,
        permissions=permissions,
        services=services,
        valid_from=request.valid_from or datetime.utcnow(),
        valid_until=request.valid_until,
        status=AuthorizationStatus.PENDING,
        created_at=datetime.utcnow()
    )
    
    # Zapisz
    authorizations_db[auth_id] = authorization
    
    if user_id not in user_authorizations_granted:
        user_authorizations_granted[user_id] = []
    user_authorizations_granted[user_id].append(auth_id)
    
    # Jeśli pełnomocnik ma konto, dodaj do jego otrzymanych
    if grantee_user_id and not grantee_user_id.startswith("pending-"):
        if grantee_user_id not in user_authorizations_received:
            user_authorizations_received[grantee_user_id] = []
        user_authorizations_received[grantee_user_id].append(auth_id)
        
        # Dodaj powiadomienie
        add_notification(
            grantee_user_id,
            ServiceType.EDORECZENIA,
            "authorization",
            "Nowe upoważnienie",
            f"{identity.name} udzielił Ci upoważnienia: {request.title}",
            f"/authorizations/{auth_id}"
        )
    
    return {
        "authorization": authorization.dict(),
        "message": "Upoważnienie utworzone" + (" i wysłane do pełnomocnika" if grantee_user_id else ". Pełnomocnik zostanie powiadomiony po rejestracji.")
    }

@app.post("/api/authorizations/{auth_id}/accept")
async def accept_authorization(
    auth_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Akceptuj otrzymane upoważnienie"""
    user_id = token_data["sub"]
    
    if auth_id not in authorizations_db:
        raise HTTPException(status_code=404, detail="Upoważnienie nie znalezione")
    
    auth = authorizations_db[auth_id]
    
    # Sprawdź czy użytkownik jest pełnomocnikiem
    user = users_db.get(user_id, {})
    if auth.grantee_email != user.get("email") and auth.grantee_user_id != user_id:
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    
    if auth.status != AuthorizationStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Upoważnienie ma status: {auth.status}")
    
    # Akceptuj
    auth.status = AuthorizationStatus.ACTIVE
    auth.accepted_at = datetime.utcnow()
    auth.grantee_user_id = user_id
    auth.grantee_name = user.get("name")
    
    # Dodaj do otrzymanych jeśli jeszcze nie ma
    if user_id not in user_authorizations_received:
        user_authorizations_received[user_id] = []
    if auth_id not in user_authorizations_received[user_id]:
        user_authorizations_received[user_id].append(auth_id)
    
    # Powiadom mocodawcę
    add_notification(
        auth.grantor_user_id,
        ServiceType.EDORECZENIA,
        "authorization",
        "Upoważnienie zaakceptowane",
        f"{auth.grantee_name or auth.grantee_email} zaakceptował upoważnienie: {auth.title}",
        f"/authorizations/{auth_id}"
    )
    
    return {"message": "Upoważnienie zaakceptowane", "authorization": auth.dict()}

@app.post("/api/authorizations/{auth_id}/reject")
async def reject_authorization(
    auth_id: str,
    reason: Optional[str] = None,
    token_data: dict = Depends(verify_jwt_token)
):
    """Odrzuć otrzymane upoważnienie"""
    user_id = token_data["sub"]
    
    if auth_id not in authorizations_db:
        raise HTTPException(status_code=404, detail="Upoważnienie nie znalezione")
    
    auth = authorizations_db[auth_id]
    user = users_db.get(user_id, {})
    
    if auth.grantee_email != user.get("email") and auth.grantee_user_id != user_id:
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    
    auth.status = AuthorizationStatus.REJECTED
    auth.revoke_reason = reason
    
    return {"message": "Upoważnienie odrzucone"}

@app.post("/api/authorizations/{auth_id}/revoke")
async def revoke_authorization(
    auth_id: str,
    reason: Optional[str] = None,
    token_data: dict = Depends(verify_jwt_token)
):
    """Odwołaj udzielone upoważnienie (przez mocodawcę)"""
    user_id = token_data["sub"]
    
    if auth_id not in authorizations_db:
        raise HTTPException(status_code=404, detail="Upoważnienie nie znalezione")
    
    auth = authorizations_db[auth_id]
    
    if auth.grantor_user_id != user_id:
        raise HTTPException(status_code=403, detail="Tylko mocodawca może odwołać upoważnienie")
    
    auth.status = AuthorizationStatus.REVOKED
    auth.revoked_at = datetime.utcnow()
    auth.revoke_reason = reason
    
    # Powiadom pełnomocnika
    if auth.grantee_user_id and not auth.grantee_user_id.startswith("pending-"):
        add_notification(
            auth.grantee_user_id,
            ServiceType.EDORECZENIA,
            "authorization",
            "Upoważnienie odwołane",
            f"Upoważnienie '{auth.title}' od {auth.grantor_name} zostało odwołane",
            None
        )
    
    return {"message": "Upoważnienie odwołane"}

@app.get("/api/authorizations/{auth_id}")
async def get_authorization(
    auth_id: str,
    token_data: dict = Depends(verify_jwt_token)
):
    """Pobierz szczegóły upoważnienia"""
    user_id = token_data["sub"]
    
    if auth_id not in authorizations_db:
        raise HTTPException(status_code=404, detail="Upoważnienie nie znalezione")
    
    auth = authorizations_db[auth_id]
    
    # Sprawdź czy użytkownik ma dostęp
    if auth.grantor_user_id != user_id and auth.grantee_user_id != user_id:
        raise HTTPException(status_code=403, detail="Brak dostępu")
    
    return {"authorization": auth.dict()}

@app.get("/api/authorizations/active-identities")
async def get_active_authorized_identities(token_data: dict = Depends(verify_jwt_token)):
    """
    Pobierz listę tożsamości, do których użytkownik ma aktywne upoważnienia.
    Używane do przełączania kontekstu (działanie w imieniu klienta).
    """
    user_id = token_data["sub"]
    
    authorized_identities = []
    
    # Pobierz aktywne upoważnienia
    for auth_id in user_authorizations_received.get(user_id, []):
        auth = authorizations_db.get(auth_id)
        if auth and auth.status == AuthorizationStatus.ACTIVE:
            # Sprawdź ważność
            if auth.valid_until and auth.valid_until < datetime.utcnow():
                auth.status = AuthorizationStatus.EXPIRED
                continue
            
            authorized_identities.append({
                "authorization_id": auth.id,
                "identity_id": auth.grantor_identity_id,
                "identity_name": auth.grantor_name,
                "type": auth.type,
                "title": auth.title,
                "permissions": auth.permissions,
                "services": auth.services,
                "valid_until": auth.valid_until.isoformat() if auth.valid_until else None
            })
    
    return {
        "authorized_identities": authorized_identities,
        "count": len(authorized_identities)
    }

@app.get("/api/authorization-types")
async def list_authorization_types():
    """Lista dostępnych typów upoważnień z opisami"""
    return {
        "types": [
            {"type": "full", "name": "Pełne pełnomocnictwo", "description": "Wszystkie uprawnienia do wszystkich usług"},
            {"type": "accounting", "name": "Księgowość", "description": "Dostęp do e-Doręczeń, KSeF, Detax AI"},
            {"type": "legal", "name": "Prawne", "description": "Dostęp do e-Doręczeń, ePUAP, podpisywanie"},
            {"type": "tax", "name": "Podatkowe", "description": "Dostęp do KSeF, Detax AI"},
            {"type": "hr", "name": "Kadry i płace", "description": "Dostęp do e-Doręczeń, ePUAP (ZUS, PIP)"},
            {"type": "edoreczenia", "name": "e-Doręczenia", "description": "Tylko e-Doręczenia"},
            {"type": "ksef", "name": "KSeF", "description": "Tylko Krajowy System e-Faktur"},
            {"type": "read_only", "name": "Tylko odczyt", "description": "Podgląd bez możliwości edycji"},
            {"type": "custom", "name": "Własne", "description": "Własny zestaw uprawnień"}
        ]
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
