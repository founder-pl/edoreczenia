"""
IMAP/SMTP Connector - Dostęp do e-Doręczeń przez protokoły email
Umożliwia korzystanie z e-Doręczeń przez standardowe klienty email
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FolderType(Enum):
    """Typy folderów IMAP"""
    INBOX = "INBOX"
    SENT = "Sent"
    DRAFTS = "Drafts"
    TRASH = "Trash"
    ARCHIVE = "Archive"
    SPAM = "Spam"


@dataclass
class IMAPFolder:
    """Folder IMAP"""
    name: str
    path: str
    folder_type: FolderType
    message_count: int = 0
    unread_count: int = 0
    subfolders: List["IMAPFolder"] = field(default_factory=list)


@dataclass
class IMAPMessage:
    """Wiadomość w formacie IMAP"""
    uid: int
    message_id: str
    subject: str
    sender: str
    recipients: List[str]
    date: datetime
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    folder: str = "INBOX"
    
    # Mapowanie z e-Doręczeń
    ade_message_id: Optional[str] = None
    ade_status: Optional[str] = None


class IMAPConnector:
    """
    IMAP Connector dla Szyfromat.pl
    Udostępnia e-Doręczenia przez protokół IMAP
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        use_ssl: bool = True,
        idcard_gateway: Optional[str] = None
    ):
        self.host = host or os.getenv("IMAP_HOST", "imap.szyfromat.pl")
        self.port = port or int(os.getenv("IMAP_PORT", "993"))
        self.use_ssl = use_ssl
        self.idcard_gateway = idcard_gateway or os.getenv("IDCARD_API_URL", "http://localhost:4000")
        
        self._connected = False
        self._username: Optional[str] = None
        self._current_folder: Optional[str] = None
        
        # In-memory storage (demo)
        self._folders: Dict[str, IMAPFolder] = {}
        self._messages: Dict[int, IMAPMessage] = {}
        self._uid_counter = 1
        
        self._init_default_folders()
    
    def _init_default_folders(self):
        """Inicjalizuj domyślne foldery IMAP"""
        default_folders = [
            IMAPFolder("INBOX", "INBOX", FolderType.INBOX),
            IMAPFolder("Sent", "Sent", FolderType.SENT),
            IMAPFolder("Drafts", "Drafts", FolderType.DRAFTS),
            IMAPFolder("Trash", "Trash", FolderType.TRASH),
            IMAPFolder("Archive", "Archive", FolderType.ARCHIVE),
            # Specjalne foldery dla e-Doręczeń
            IMAPFolder("e-Doręczenia", "e-Doreczenia", FolderType.INBOX, subfolders=[
                IMAPFolder("Urzędowe", "e-Doreczenia/Urzedowe", FolderType.INBOX),
                IMAPFolder("Prywatne", "e-Doreczenia/Prywatne", FolderType.INBOX),
                IMAPFolder("Firmowe", "e-Doreczenia/Firmowe", FolderType.INBOX),
            ]),
        ]
        
        for folder in default_folders:
            self._folders[folder.path] = folder
    
    # ═══════════════════════════════════════════════════════════════
    # CONNECTION
    # ═══════════════════════════════════════════════════════════════
    
    def connect(self, username: str, password: str) -> bool:
        """
        Połącz z serwerem IMAP
        
        Args:
            username: Nazwa użytkownika (email lub adres ADE)
            password: Hasło lub token
        
        Returns:
            True jeśli połączono pomyślnie
        """
        logger.info(f"IMAP connecting: {username}@{self.host}:{self.port}")
        
        # W produkcji: prawdziwe połączenie IMAP
        # import imaplib
        # self._imap = imaplib.IMAP4_SSL(self.host, self.port)
        # self._imap.login(username, password)
        
        self._connected = True
        self._username = username
        self._current_folder = "INBOX"
        
        logger.info(f"IMAP connected: {username}")
        return True
    
    def connect_via_idcard(self, idcard_token: str) -> bool:
        """Połącz przez IDCard.pl Gateway"""
        logger.info("IMAP connecting via IDCard.pl")
        
        # W produkcji: weryfikacja tokenu przez IDCard.pl
        self._connected = True
        return True
    
    def disconnect(self) -> bool:
        """Rozłącz z serwerem IMAP"""
        if self._connected:
            logger.info(f"IMAP disconnecting: {self._username}")
            self._connected = False
            self._username = None
            return True
        return False
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    # ═══════════════════════════════════════════════════════════════
    # FOLDERS
    # ═══════════════════════════════════════════════════════════════
    
    def list_folders(self) -> List[IMAPFolder]:
        """Lista folderów"""
        if not self._connected:
            raise RuntimeError("Not connected")
        return list(self._folders.values())
    
    def select_folder(self, folder_path: str) -> IMAPFolder:
        """Wybierz folder"""
        if folder_path not in self._folders:
            raise ValueError(f"Folder not found: {folder_path}")
        
        self._current_folder = folder_path
        return self._folders[folder_path]
    
    def create_folder(self, folder_path: str, folder_type: FolderType = FolderType.INBOX) -> IMAPFolder:
        """Utwórz nowy folder"""
        name = folder_path.split("/")[-1]
        folder = IMAPFolder(name, folder_path, folder_type)
        self._folders[folder_path] = folder
        return folder
    
    def delete_folder(self, folder_path: str) -> bool:
        """Usuń folder"""
        if folder_path in self._folders:
            del self._folders[folder_path]
            return True
        return False
    
    # ═══════════════════════════════════════════════════════════════
    # MESSAGES
    # ═══════════════════════════════════════════════════════════════
    
    def fetch_messages(
        self,
        folder: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        search_criteria: Optional[str] = None
    ) -> List[IMAPMessage]:
        """
        Pobierz wiadomości z folderu
        
        Args:
            folder: Ścieżka folderu (domyślnie: aktualny)
            limit: Maksymalna liczba wiadomości
            offset: Offset dla paginacji
            search_criteria: Kryteria wyszukiwania IMAP
        
        Returns:
            Lista wiadomości
        """
        if not self._connected:
            raise RuntimeError("Not connected")
        
        folder = folder or self._current_folder
        
        messages = [m for m in self._messages.values() if m.folder == folder]
        messages.sort(key=lambda m: m.date, reverse=True)
        
        return messages[offset:offset + limit]
    
    def fetch_message(self, uid: int) -> Optional[IMAPMessage]:
        """Pobierz pojedynczą wiadomość"""
        return self._messages.get(uid)
    
    def store_message(self, message: IMAPMessage) -> int:
        """
        Zapisz wiadomość (mapowanie z e-Doręczeń)
        
        Returns:
            UID wiadomości
        """
        uid = self._uid_counter
        self._uid_counter += 1
        
        message.uid = uid
        self._messages[uid] = message
        
        # Aktualizuj liczniki folderu
        if message.folder in self._folders:
            self._folders[message.folder].message_count += 1
            if "\\Seen" not in message.flags:
                self._folders[message.folder].unread_count += 1
        
        return uid
    
    def move_message(self, uid: int, target_folder: str) -> bool:
        """Przenieś wiadomość do innego folderu"""
        if uid in self._messages and target_folder in self._folders:
            old_folder = self._messages[uid].folder
            self._messages[uid].folder = target_folder
            
            # Aktualizuj liczniki
            self._folders[old_folder].message_count -= 1
            self._folders[target_folder].message_count += 1
            
            return True
        return False
    
    def delete_message(self, uid: int) -> bool:
        """Usuń wiadomość (przenieś do kosza)"""
        return self.move_message(uid, "Trash")
    
    def set_flags(self, uid: int, flags: List[str]) -> bool:
        """Ustaw flagi wiadomości"""
        if uid in self._messages:
            self._messages[uid].flags = flags
            return True
        return False
    
    def add_flag(self, uid: int, flag: str) -> bool:
        """Dodaj flagę do wiadomości"""
        if uid in self._messages:
            if flag not in self._messages[uid].flags:
                self._messages[uid].flags.append(flag)
            return True
        return False
    
    # ═══════════════════════════════════════════════════════════════
    # ADE MAPPING
    # ═══════════════════════════════════════════════════════════════
    
    def import_from_ade(self, ade_message: Dict[str, Any]) -> IMAPMessage:
        """
        Importuj wiadomość z e-Doręczeń do formatu IMAP
        
        Args:
            ade_message: Wiadomość z ADE Connector
        
        Returns:
            Wiadomość w formacie IMAP
        """
        message = IMAPMessage(
            uid=0,  # Zostanie nadany przy store
            message_id=f"<{ade_message['id']}@edoreczenia.gov.pl>",
            subject=ade_message.get("subject", ""),
            sender=ade_message.get("sender", {}).get("address", ""),
            recipients=[ade_message.get("recipient", {}).get("address", "")],
            date=datetime.fromisoformat(ade_message.get("sent_at", datetime.utcnow().isoformat())),
            body_text=ade_message.get("content", ""),
            attachments=ade_message.get("attachments", []),
            folder="INBOX",
            ade_message_id=ade_message.get("id"),
            ade_status=ade_message.get("status")
        )
        
        return message
    
    def export_to_ade(self, imap_message: IMAPMessage) -> Dict[str, Any]:
        """
        Eksportuj wiadomość IMAP do formatu e-Doręczeń
        
        Args:
            imap_message: Wiadomość IMAP
        
        Returns:
            Wiadomość w formacie ADE
        """
        return {
            "recipient": imap_message.recipients[0] if imap_message.recipients else "",
            "subject": imap_message.subject,
            "content": imap_message.body_text or "",
            "attachments": imap_message.attachments
        }
    
    # ═══════════════════════════════════════════════════════════════
    # STATUS
    # ═══════════════════════════════════════════════════════════════
    
    def get_status(self) -> Dict[str, Any]:
        """Pobierz status połączenia"""
        return {
            "connected": self._connected,
            "username": self._username,
            "host": self.host,
            "port": self.port,
            "current_folder": self._current_folder,
            "folders_count": len(self._folders),
            "messages_count": len(self._messages)
        }


class SMTPConnector:
    """
    SMTP Connector dla Szyfromat.pl
    Wysyłanie e-Doręczeń przez protokół SMTP
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        use_tls: bool = True
    ):
        self.host = host or os.getenv("SMTP_HOST", "smtp.szyfromat.pl")
        self.port = port or int(os.getenv("SMTP_PORT", "587"))
        self.use_tls = use_tls
        
        self._connected = False
        self._username: Optional[str] = None
    
    def connect(self, username: str, password: str) -> bool:
        """Połącz z serwerem SMTP"""
        logger.info(f"SMTP connecting: {username}@{self.host}:{self.port}")
        
        # W produkcji: prawdziwe połączenie SMTP
        # import smtplib
        # self._smtp = smtplib.SMTP(self.host, self.port)
        # self._smtp.starttls()
        # self._smtp.login(username, password)
        
        self._connected = True
        self._username = username
        return True
    
    def disconnect(self) -> bool:
        """Rozłącz z serwerem SMTP"""
        if self._connected:
            self._connected = False
            self._username = None
            return True
        return False
    
    def send_message(
        self,
        to: List[str],
        subject: str,
        body: str,
        attachments: Optional[List[Dict]] = None,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Wyślij wiadomość przez SMTP (mapowane na e-Doręczenia)
        
        Args:
            to: Lista odbiorców (adresy ADE)
            subject: Temat
            body: Treść tekstowa
            attachments: Załączniki
            html_body: Treść HTML
        
        Returns:
            True jeśli wysłano pomyślnie
        """
        if not self._connected:
            raise RuntimeError("Not connected")
        
        logger.info(f"SMTP sending to: {to}")
        
        # W produkcji: mapowanie na API e-Doręczeń
        return True
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def get_status(self) -> Dict[str, Any]:
        """Pobierz status połączenia"""
        return {
            "connected": self._connected,
            "username": self._username,
            "host": self.host,
            "port": self.port
        }
