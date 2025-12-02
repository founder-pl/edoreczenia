"""
Symulator API e-Doręczeń dla celów testowych.
Emuluje REST API zgodne ze specyfikacją UA API v5.
"""
import base64
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Header, Query, status
from fastapi.responses import JSONResponse, Response
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

app = FastAPI(
    title="User Agent API - Symulator",
    description="Symulator REST API e-Doręczeń zgodny ze specyfikacją UA API v3.0.8",
    version="3.0.8",
)

# Aliasy dla kompatybilności - obsługujemy zarówno /api/v1 jak i /ua/v5
API_PREFIX_V1 = "/api/v1"
API_PREFIX_V5 = "/ua/v5"

# ============================================
# Storage (in-memory)
# ============================================

# Przechowywanie danych w pamięci
tokens: dict[str, dict] = {}
messages: dict[str, dict[str, Any]] = {}  # message_id -> message
attachments: dict[str, bytes] = {}  # attachment_id -> content
epo_records: dict[str, dict] = {}  # message_id -> EPO

# Konfiguracja testowa
TEST_CLIENT_ID = "test_client_id"
TEST_CLIENT_SECRET = "test_client_secret"
TEST_ADDRESS = "AE:PL-12345-67890-ABCDE-12"

# Inicjalizacja przykładowych wiadomości
def init_sample_data():
    """Inicjalizuje przykładowe dane."""
    sample_messages = [
        {
            "messageId": "msg-001",
            "subject": "Decyzja administracyjna nr 123/2024",
            "sender": {"address": "AE:PL-URZAD-MIAS-TOWAR-01", "name": "Urząd Miasta"},
            "recipients": [{"address": TEST_ADDRESS, "name": "Odbiorca testowy"}],
            "content": "Szanowny Panie/Pani,\n\nNiniejszym informujemy o wydaniu decyzji administracyjnej...",
            "contentHtml": "<p>Szanowny Panie/Pani,</p><p>Niniejszym informujemy o wydaniu decyzji administracyjnej...</p>",
            "attachments": [
                {
                    "attachmentId": "att-001",
                    "filename": "decyzja_123_2024.pdf",
                    "contentType": "application/pdf",
                    "size": 15420,
                }
            ],
            "receivedAt": (datetime.now() - timedelta(hours=2)).isoformat(),
            "status": "RECEIVED",
            "folder": "inbox",
        },
        {
            "messageId": "msg-002",
            "subject": "Zawiadomienie o terminie rozprawy",
            "sender": {"address": "AE:PL-SADRE-JONO-WYYYY-02", "name": "Sąd Rejonowy"},
            "recipients": [{"address": TEST_ADDRESS, "name": "Odbiorca testowy"}],
            "content": "Uprzejmie zawiadamiamy o wyznaczeniu terminu rozprawy na dzień...",
            "contentHtml": None,
            "attachments": [],
            "receivedAt": (datetime.now() - timedelta(days=1)).isoformat(),
            "status": "READ",
            "folder": "inbox",
        },
        {
            "messageId": "msg-003",
            "subject": "Wezwanie do uzupełnienia dokumentów",
            "sender": {"address": "AE:PL-ZUSWA-RSZW-AODZ-03", "name": "ZUS"},
            "recipients": [{"address": TEST_ADDRESS, "name": "Odbiorca testowy"}],
            "content": "W związku ze złożonym wnioskiem wzywamy do uzupełnienia...",
            "contentHtml": "<p>W związku ze złożonym wnioskiem wzywamy do uzupełnienia...</p>",
            "attachments": [
                {
                    "attachmentId": "att-002",
                    "filename": "formularz_uzupelnienie.pdf",
                    "contentType": "application/pdf",
                    "size": 8200,
                },
                {
                    "attachmentId": "att-003",
                    "filename": "instrukcja.docx",
                    "contentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "size": 24500,
                },
            ],
            "receivedAt": (datetime.now() - timedelta(days=3)).isoformat(),
            "status": "RECEIVED",
            "folder": "inbox",
        },
    ]

    for msg in sample_messages:
        messages[msg["messageId"]] = msg

    # Przykładowe załączniki (symulowane dane binarne)
    attachments["att-001"] = b"%PDF-1.4 fake pdf content for testing purposes..." * 100
    attachments["att-002"] = b"%PDF-1.4 another fake pdf content..." * 50
    attachments["att-003"] = b"PK fake docx content..." * 100

    # Przykładowe EPO
    epo_records["msg-002"] = {
        "messageId": "msg-002",
        "epoId": "epo-002",
        "receivedAt": (datetime.now() - timedelta(days=1, hours=1)).isoformat(),
        "openedAt": (datetime.now() - timedelta(days=1)).isoformat(),
        "recipientAddress": TEST_ADDRESS,
        "status": "CONFIRMED",
    }


init_sample_data()


# ============================================
# Models
# ============================================


class TokenRequest(BaseModel):
    grant_type: str
    client_id: str
    client_secret: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600


class Recipient(BaseModel):
    address: str
    name: Optional[str] = None


class Attachment(BaseModel):
    filename: str
    contentType: str
    content: str  # Base64


class SendMessageRequest(BaseModel):
    recipients: list[Recipient]
    subject: str
    content: str
    contentHtml: Optional[str] = None
    attachments: Optional[list[Attachment]] = None


class UpdateStatusRequest(BaseModel):
    status: str


class MessageResponse(BaseModel):
    messageId: str
    subject: str
    sender: dict
    recipients: list[dict]
    content: str
    contentHtml: Optional[str]
    attachments: list[dict]
    receivedAt: str
    status: str
    folder: str


class MessagesListResponse(BaseModel):
    messages: list[dict]
    total: int
    offset: int
    limit: int


# ============================================
# Auth
# ============================================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="oauth/token", auto_error=False)


def verify_token(authorization: Optional[str] = Header(None)) -> str:
    """Weryfikuje token autoryzacyjny."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = authorization[7:]

    if token not in tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    token_data = tokens[token]
    if datetime.fromisoformat(token_data["expires_at"]) < datetime.now():
        del tokens[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    return token


# ============================================
# Endpoints
# ============================================


@app.post("/oauth/token", response_model=TokenResponse)
async def get_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
):
    """Endpoint OAuth2 do uzyskania tokenu (form-urlencoded zgodnie z RFC 6749)."""
    if grant_type != "client_credentials":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported grant type",
        )

    if client_id != TEST_CLIENT_ID or client_secret != TEST_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
        )

    # Generuj nowy token
    access_token = secrets.token_urlsafe(32)
    expires_in = 3600

    tokens[access_token] = {
        "client_id": client_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
    }

    return TokenResponse(access_token=access_token, expires_in=expires_in)


async def _get_messages_impl(
    address: str,
    offset: int = 0,
    limit: int = 20,
    format: str = "minimal",
    sender: Optional[str] = None,
    recipient: Optional[str] = None,
    subject: Optional[str] = None,
    label: Optional[str] = None,
    opened: Optional[bool] = None,
    attachments_filter: Optional[bool] = None,
    sortColumn: Optional[str] = None,
    sortDirection: Optional[str] = None,
):
    """Implementacja pobierania listy wiadomości zgodna z UA API v3.0.8."""
    if address != TEST_ADDRESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this address",
        )

    # Filtrowanie wiadomości
    filtered = list(messages.values())
    
    # Filtr po folderze/etykiecie
    if label:
        filtered = [msg for msg in filtered if msg.get("folder") == label or label in msg.get("labels", [])]
    
    # Filtr po nadawcy
    if sender:
        filtered = [msg for msg in filtered if sender.lower() in str(msg.get("sender", {})).lower()]
    
    # Filtr po odbiorcy
    if recipient:
        filtered = [msg for msg in filtered if any(recipient.lower() in str(r).lower() for r in msg.get("recipients", []))]
    
    # Filtr po temacie
    if subject:
        filtered = [msg for msg in filtered if subject.lower() in msg.get("subject", "").lower()]
    
    # Filtr po odczytaniu
    if opened is not None:
        filtered = [msg for msg in filtered if msg.get("opened", False) == opened]
    
    # Filtr po załącznikach
    if attachments_filter is not None:
        filtered = [msg for msg in filtered if bool(msg.get("attachments")) == attachments_filter]

    # Sortowanie
    sort_key = sortColumn or "receivedAt"
    reverse = sortDirection != "asc"
    
    key_mapping = {
        "sender": lambda x: str(x.get("sender", {}).get("name", "")),
        "recipient": lambda x: str(x.get("recipients", [{}])[0].get("name", "") if x.get("recipients") else ""),
        "subject": lambda x: x.get("subject", ""),
        "submissionDate": lambda x: x.get("submissionDate", x.get("receivedAt", "")),
        "eventDate": lambda x: x.get("eventDate", x.get("receivedAt", "")),
        "receiptDate": lambda x: x.get("receiptDate", x.get("receivedAt", "")),
        "timestamp": lambda x: x.get("receivedAt", ""),
    }
    
    if sort_key in key_mapping:
        filtered.sort(key=key_mapping[sort_key], reverse=reverse)
    else:
        filtered.sort(key=lambda x: x.get("receivedAt", ""), reverse=reverse)

    # Paginacja
    total = len(filtered)
    paginated = filtered[offset:offset + limit]

    return MessagesListResponse(
        messages=paginated,
        total=total,
        offset=offset,
        limit=limit,
    )


@app.get("/api/v1/{address}/messages", response_model=MessagesListResponse)
@app.get("/ua/v5/{address}/messages", response_model=MessagesListResponse)
async def get_messages(
    address: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=2000),
    format: str = Query(default="minimal", enum=["metadata", "minimal"]),
    sender: Optional[str] = Query(default=None),
    recipient: Optional[str] = Query(default=None),
    subject: Optional[str] = Query(default=None),
    label: Optional[str] = Query(default=None, description="Folder/etykieta (zgodne z dokumentacją)"),
    folder: Optional[str] = Query(default=None, description="Folder (alias dla label)"),
    opened: Optional[bool] = Query(default=None),
    attachments: Optional[bool] = Query(default=None, alias="attachments"),
    sortColumn: Optional[str] = Query(default=None, enum=["sender", "recipient", "subject", "submissionDate", "eventDate", "receiptDate", "timestamp"]),
    sortDirection: Optional[str] = Query(default=None, enum=["asc", "desc"]),
    token: str = Depends(verify_token),
):
    """Pobiera listę wiadomości (GET /{eDeliveryAddress}/messages)."""
    # Obsługa obu parametrów: label (dokumentacja) i folder (kompatybilność)
    effective_label = label or folder
    
    return await _get_messages_impl(
        address=address,
        offset=offset,
        limit=limit,
        format=format,
        sender=sender,
        recipient=recipient,
        subject=subject,
        label=effective_label,
        opened=opened,
        attachments_filter=attachments,
        sortColumn=sortColumn,
        sortDirection=sortDirection,
    )


@app.get("/api/v1/{address}/messages/{message_id}")
@app.get("/ua/v5/{address}/messages/{message_id}")
async def get_message(
    address: str,
    message_id: str,
    format: str = Query(default="full", enum=["fullExtended", "full", "metadata", "minimal"]),
    token: str = Depends(verify_token),
):
    """Pobiera szczegóły wiadomości (GET /{eDeliveryAddress}/messages/{messageId})."""
    if address != TEST_ADDRESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this address",
        )

    if message_id not in messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    msg = messages[message_id].copy()
    
    # Oznacz jako odczytaną przy pobraniu w trybie full
    if format in ("full", "fullExtended"):
        messages[message_id]["opened"] = True
        messages[message_id]["status"] = "READ"
    
    return [msg]  # API zwraca tablicę


@app.get("/api/v1/{address}/messages/{message_id}/attachments/{attachment_id}")
@app.get("/ua/v5/{address}/messages/{message_id}/attachments/{attachment_id}")
async def get_attachment(
    address: str,
    message_id: str,
    attachment_id: str,
    token: str = Depends(verify_token),
):
    """Pobiera załącznik (GET /{eDeliveryAddress}/messages/{messageId}/attachments/{attachmentId})."""
    if address != TEST_ADDRESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if message_id not in messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    if attachment_id not in attachments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    # Znajdź metadane załącznika
    msg = messages[message_id]
    att_meta = next(
        (a for a in msg.get("attachments", []) if a["attachmentId"] == attachment_id),
        None,
    )

    if not att_meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found in message",
        )

    return Response(
        content=attachments[attachment_id],
        media_type=att_meta["contentType"],
        headers={
            "Content-Disposition": f'attachment; filename="{att_meta["filename"]}"',
        },
    )


@app.post("/api/v1/{address}/messages", status_code=202)
@app.post("/ua/v5/{address}/messages", status_code=202)
async def send_message(
    address: str,
    request: SendMessageRequest,
    token: str = Depends(verify_token),
):
    """Wysyła nową wiadomość (POST /{eDeliveryAddress}/messages)."""
    if address != TEST_ADDRESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Generuj ID wiadomości
    message_id = f"msg-{uuid.uuid4().hex[:8]}"

    # Przetwórz załączniki
    msg_attachments = []
    if request.attachments:
        for att in request.attachments:
            att_id = f"att-{uuid.uuid4().hex[:8]}"
            attachments[att_id] = base64.b64decode(att.content)
            msg_attachments.append({
                "attachmentId": att_id,
                "filename": att.filename,
                "contentType": att.contentType,
                "size": len(attachments[att_id]),
            })

    # Utwórz wiadomość
    new_message = {
        "messageId": message_id,
        "subject": request.subject,
        "sender": {"address": address, "name": "Nadawca testowy"},
        "recipients": [r.model_dump() for r in request.recipients],
        "content": request.content,
        "contentHtml": request.contentHtml,
        "attachments": msg_attachments,
        "receivedAt": datetime.now().isoformat(),
        "status": "SENT",
        "folder": "sent",
    }

    messages[message_id] = new_message

    return {
        "messageId": message_id,
        "status": "SENT",
        "sentAt": datetime.now().isoformat(),
    }


@app.patch("/api/v1/{address}/messages/{message_id}/message_control_data")
@app.patch("/ua/v5/{address}/messages/{message_id}/message_control_data")
async def update_message_control_data(
    address: str,
    message_id: str,
    request: UpdateStatusRequest,
    token: str = Depends(verify_token),
):
    """Aktualizuje status wiadomości."""
    if address != TEST_ADDRESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if message_id not in messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    valid_statuses = ["RECEIVED", "READ", "OPENED", "ARCHIVED", "DELETED"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Valid values: {valid_statuses}",
        )

    messages[message_id]["status"] = request.status

    return {"messageId": message_id, "status": request.status}


@app.get("/api/v1/{address}/messages/{message_id}/evidences")
@app.get("/ua/v5/{address}/messages/{message_id}/evidences")
async def get_evidences(
    address: str,
    message_id: str,
    token: str = Depends(verify_token),
):
    """Pobiera Elektroniczne Poświadczenie Odbioru."""
    if address != TEST_ADDRESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if message_id not in messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    if message_id not in epo_records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="EPO not available for this message",
        )

    return epo_records[message_id]


@app.delete("/api/v1/{address}/messages/{message_id}")
@app.delete("/ua/v5/{address}/messages/{message_id}")
async def delete_message(
    address: str,
    message_id: str,
    token: str = Depends(verify_token),
):
    """Usuwa wiadomość (DELETE /{eDeliveryAddress}/messages/{messageId})."""
    if address != TEST_ADDRESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if message_id not in messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    del messages[message_id]
    return [{"messageId": message_id}]


@app.get("/api/v1/{address}/directories")
@app.get("/ua/v5/{address}/directories")
async def get_directories(
    address: str,
    token: str = Depends(verify_token),
):
    """Pobiera listę katalogów (GET /{eDeliveryAddress}/directories)."""
    if address != TEST_ADDRESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Zgodnie z dokumentacją - zwracamy katalogi predefiniowane i definiowane
    return {
        "directories": [
            {"directoryId": "inbox", "name": "Odebrane", "label": "INBOX", "type": "predefined"},
            {"directoryId": "sent", "name": "Wysłane", "label": "SENT", "type": "predefined"},
            {"directoryId": "drafts", "name": "Robocze", "label": "DRAFTS", "type": "predefined"},
            {"directoryId": "trash", "name": "Kosz", "label": "TRASH", "type": "predefined"},
            {"directoryId": "archive", "name": "Archiwum", "label": "ARCHIVE", "type": "predefined"},
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "User Agent API Simulator",
        "version": "3.0.8",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint z informacjami."""
    return {
        "service": "Symulator User Agent API e-Doręczeń",
        "version": "3.0.8",
        "spec": "UA API v3.0.8.1",
        "documentation": "/docs",
        "health": "/health",
        "endpoints": {
            "api_v1": "/api/v1/{eDeliveryAddress}/messages",
            "ua_v5": "/ua/v5/{eDeliveryAddress}/messages",
        },
        "test_credentials": {
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
            "test_address": TEST_ADDRESS,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
