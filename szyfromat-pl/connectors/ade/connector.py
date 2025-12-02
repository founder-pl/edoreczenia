"""
ADE Connector - Integracja z adresami e-Doręczeń
Obsługa komunikacji z systemem e-Doręczeń gov.pl
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ADEStatus(Enum):
    """Status adresu ADE"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


class MessageStatus(Enum):
    """Status wiadomości e-Doręczeń"""
    DRAFT = "draft"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


@dataclass
class ADEAddress:
    """Adres e-Doręczeń"""
    address: str  # AE:PL-XXX-XXX-XXXX-XX
    name: str
    organization: Optional[str] = None
    status: ADEStatus = ADEStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_valid(self) -> bool:
        return self.address.startswith("AE:PL-") and self.status == ADEStatus.ACTIVE


@dataclass
class ADEMessage:
    """Wiadomość e-Doręczeń"""
    id: str
    sender: ADEAddress
    recipient: ADEAddress
    subject: str
    content: str
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    status: MessageStatus = MessageStatus.DRAFT
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ADEConnector:
    """
    Connector do systemu e-Doręczeń (ADE)
    Obsługuje komunikację z gov.pl API
    """
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        idcard_gateway: Optional[str] = None
    ):
        self.api_url = api_url or os.getenv("ADE_API_URL", "https://edoreczenia.gov.pl/api")
        self.client_id = client_id or os.getenv("ADE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("ADE_CLIENT_SECRET")
        self.idcard_gateway = idcard_gateway or os.getenv("IDCARD_API_URL", "http://localhost:4000")
        
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._connected_address: Optional[ADEAddress] = None
        
        # In-memory storage (demo)
        self._messages: Dict[str, ADEMessage] = {}
        self._addresses: Dict[str, ADEAddress] = {}
    
    # ═══════════════════════════════════════════════════════════════
    # CONNECTION
    # ═══════════════════════════════════════════════════════════════
    
    def connect(self, ade_address: str, auth_method: str = "oauth2") -> bool:
        """
        Połącz z adresem e-Doręczeń
        
        Args:
            ade_address: Adres ADE (AE:PL-XXX-XXX-XXXX-XX)
            auth_method: Metoda autoryzacji (oauth2, mobywatel, certificate)
        
        Returns:
            True jeśli połączono pomyślnie
        """
        logger.info(f"Connecting to ADE address: {ade_address}")
        
        if not ade_address.startswith("AE:PL-"):
            raise ValueError(f"Invalid ADE address format: {ade_address}")
        
        # Symulacja połączenia (w produkcji: OAuth2 flow)
        self._connected_address = ADEAddress(
            address=ade_address,
            name="Connected User",
            status=ADEStatus.ACTIVE
        )
        
        self._addresses[ade_address] = self._connected_address
        
        logger.info(f"Connected to ADE: {ade_address}")
        return True
    
    def connect_via_idcard(self, idcard_token: str) -> bool:
        """
        Połącz przez IDCard.pl Gateway
        
        Args:
            idcard_token: Token z IDCard.pl
        
        Returns:
            True jeśli połączono pomyślnie
        """
        logger.info("Connecting via IDCard.pl gateway")
        
        # W produkcji: wywołanie API IDCard.pl
        # response = requests.get(
        #     f"{self.idcard_gateway}/api/services/connections",
        #     headers={"Authorization": f"Bearer {idcard_token}"}
        # )
        
        return True
    
    def disconnect(self) -> bool:
        """Rozłącz z adresem ADE"""
        if self._connected_address:
            logger.info(f"Disconnecting from ADE: {self._connected_address.address}")
            self._connected_address = None
            return True
        return False
    
    @property
    def is_connected(self) -> bool:
        return self._connected_address is not None
    
    @property
    def current_address(self) -> Optional[ADEAddress]:
        return self._connected_address
    
    # ═══════════════════════════════════════════════════════════════
    # MESSAGES
    # ═══════════════════════════════════════════════════════════════
    
    def send_message(
        self,
        recipient: str,
        subject: str,
        content: str,
        attachments: Optional[List[Dict]] = None
    ) -> ADEMessage:
        """
        Wyślij wiadomość e-Doręczeń
        
        Args:
            recipient: Adres ADE odbiorcy
            subject: Temat wiadomości
            content: Treść wiadomości
            attachments: Lista załączników
        
        Returns:
            Wysłana wiadomość
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to ADE address")
        
        import uuid
        message_id = f"msg-{uuid.uuid4().hex[:8]}"
        
        recipient_addr = ADEAddress(
            address=recipient,
            name="Recipient",
            status=ADEStatus.ACTIVE
        )
        
        message = ADEMessage(
            id=message_id,
            sender=self._connected_address,
            recipient=recipient_addr,
            subject=subject,
            content=content,
            attachments=attachments or [],
            status=MessageStatus.SENT,
            sent_at=datetime.utcnow()
        )
        
        self._messages[message_id] = message
        
        logger.info(f"Message sent: {message_id} to {recipient}")
        return message
    
    def fetch_messages(
        self,
        folder: str = "inbox",
        limit: int = 50,
        offset: int = 0
    ) -> List[ADEMessage]:
        """
        Pobierz wiadomości
        
        Args:
            folder: Folder (inbox, sent, drafts, trash)
            limit: Maksymalna liczba wiadomości
            offset: Offset dla paginacji
        
        Returns:
            Lista wiadomości
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to ADE address")
        
        messages = list(self._messages.values())
        
        if folder == "inbox":
            messages = [m for m in messages if m.recipient.address == self._connected_address.address]
        elif folder == "sent":
            messages = [m for m in messages if m.sender.address == self._connected_address.address]
        
        return messages[offset:offset + limit]
    
    def get_message(self, message_id: str) -> Optional[ADEMessage]:
        """Pobierz pojedynczą wiadomość"""
        return self._messages.get(message_id)
    
    def mark_as_read(self, message_id: str) -> bool:
        """Oznacz wiadomość jako przeczytaną"""
        if message_id in self._messages:
            self._messages[message_id].status = MessageStatus.READ
            self._messages[message_id].read_at = datetime.utcnow()
            return True
        return False
    
    def delete_message(self, message_id: str) -> bool:
        """Usuń wiadomość"""
        if message_id in self._messages:
            del self._messages[message_id]
            return True
        return False
    
    # ═══════════════════════════════════════════════════════════════
    # ATTACHMENTS
    # ═══════════════════════════════════════════════════════════════
    
    def upload_attachment(
        self,
        message_id: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """
        Dodaj załącznik do wiadomości
        
        Returns:
            Metadane załącznika
        """
        import uuid
        attachment_id = f"att-{uuid.uuid4().hex[:8]}"
        
        attachment = {
            "id": attachment_id,
            "filename": filename,
            "size": len(content),
            "content_type": content_type,
            "uploaded_at": datetime.utcnow().isoformat()
        }
        
        if message_id in self._messages:
            self._messages[message_id].attachments.append(attachment)
        
        return attachment
    
    def download_attachment(self, message_id: str, attachment_id: str) -> Optional[bytes]:
        """Pobierz załącznik"""
        # W produkcji: pobieranie z API
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # ADDRESS BOOK
    # ═══════════════════════════════════════════════════════════════
    
    def lookup_address(self, query: str) -> List[ADEAddress]:
        """
        Wyszukaj adres ADE
        
        Args:
            query: NIP, REGON, PESEL lub nazwa
        
        Returns:
            Lista pasujących adresów
        """
        # W produkcji: wywołanie API rejestru ADE
        return []
    
    def validate_address(self, ade_address: str) -> bool:
        """Sprawdź czy adres ADE jest prawidłowy"""
        if not ade_address.startswith("AE:PL-"):
            return False
        
        parts = ade_address.split("-")
        return len(parts) >= 4
    
    # ═══════════════════════════════════════════════════════════════
    # STATUS
    # ═══════════════════════════════════════════════════════════════
    
    def get_status(self) -> Dict[str, Any]:
        """Pobierz status połączenia"""
        return {
            "connected": self.is_connected,
            "address": self._connected_address.address if self._connected_address else None,
            "messages_count": len(self._messages),
            "api_url": self.api_url,
            "idcard_gateway": self.idcard_gateway
        }
