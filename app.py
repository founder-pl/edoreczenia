"""
Symulator API e-Doręczeń dla celów testowych.
Emuluje REST API zgodne ze specyfikacją UA API v5.
"""
import base64
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Header, Query, status
from fastapi.responses import JSONResponse, Response
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

app = FastAPI(
    title="Symulator API e-Doręczeń",
    description="Symulator REST API e-Doręczeń dla celów testowych i deweloperskich",
    version="5.0.0",
)

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
async def get_token(request: TokenRequest):
    """Endpoint OAuth2 do uzyskania tokenu."""
    if request.grant_type != "client_credentials":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported grant type",
        )

    if request.client_id != TEST_CLIENT_ID or request.client_secret != TEST_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
        )

    # Generuj nowy token
    access_token = secrets.token_urlsafe(32)
    expires_in = 3600

    tokens[access_token] = {
        "client_id": request.client_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
    }

    return TokenResponse(access_token=access_token, expires_in=expires_in)


@app.get("/ua/v5/{address}/messages", response_model=MessagesListResponse)
async def get_messages(
    address: str,
    folder: str = Query(default="inbox"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0),
    since: Optional[str] = Query(default=None),
    token: str = Depends(verify_token),
):
    """Pobiera listę wiadomości."""
    if address != TEST_ADDRESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this address",
        )

    # Filtrowanie wiadomości
    filtered = [
        msg for msg in messages.values()
        if msg.get("folder") == folder
    ]

    # Filtr po dacie
    if since:
        since_dt = datetime.fromisoformat(since)
        filtered = [
            msg for msg in filtered
            if datetime.fromisoformat(msg["receivedAt"]) > since_dt
        ]

    # Sortowanie po dacie (najnowsze pierwsze)
    filtered.sort(key=lambda x: x["receivedAt"], reverse=True)

    # Paginacja
    total = len(filtered)
    paginated = filtered[offset:offset + limit]

    return MessagesListResponse(
        messages=paginated,
        total=total,
        offset=offset,
        limit=limit,
    )


@app.get("/ua/v5/{address}/messages/{message_id}")
async def get_message(
    address: str,
    message_id: str,
    token: str = Depends(verify_token),
):
    """Pobiera szczegóły wiadomości."""
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

    return messages[message_id]


@app.get("/ua/v5/{address}/messages/{message_id}/attachments/{attachment_id}")
async def get_attachment(
    address: str,
    message_id: str,
    attachment_id: str,
    token: str = Depends(verify_token),
):
    """Pobiera załącznik."""
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


@app.post("/ua/v5/{address}/messages")
async def send_message(
    address: str,
    request: SendMessageRequest,
    token: str = Depends(verify_token),
):
    """Wysyła nową wiadomość."""
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


@app.put("/ua/v5/{address}/messages/{message_id}/status")
async def update_message_status(
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


@app.get("/ua/v5/{address}/messages/{message_id}/epo")
async def get_epo(
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


@app.get("/ua/v5/{address}/folders")
async def get_folders(
    address: str,
    token: str = Depends(verify_token),
):
    """Pobiera listę folderów."""
    if address != TEST_ADDRESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return {
        "folders": [
            {"name": "inbox", "displayName": "Odebrane", "unread": 2},
            {"name": "sent", "displayName": "Wysłane", "unread": 0},
            {"name": "drafts", "displayName": "Robocze", "unread": 0},
            {"name": "trash", "displayName": "Kosz", "unread": 0},
            {"name": "archive", "displayName": "Archiwum", "unread": 0},
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "e-Doreczenia Simulator",
        "version": "5.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint z informacjami."""
    return {
        "service": "Symulator API e-Doręczeń",
        "version": "5.0.0",
        "documentation": "/docs",
        "health": "/health",
        "test_credentials": {
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
            "test_address": TEST_ADDRESS,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
