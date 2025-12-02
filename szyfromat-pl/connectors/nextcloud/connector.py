"""
Nextcloud Connector - Przechowywanie załączników w chmurze
Integracja z Nextcloud dla załączników e-Doręczeń
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import base64
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class NextcloudFile:
    """Plik w Nextcloud"""
    id: str
    name: str
    path: str
    size: int
    content_type: str
    etag: str
    modified_at: datetime
    is_directory: bool = False
    
    # Metadane e-Doręczeń
    ade_message_id: Optional[str] = None
    ade_attachment_id: Optional[str] = None


@dataclass
class NextcloudFolder:
    """Folder w Nextcloud"""
    name: str
    path: str
    files: List[NextcloudFile] = field(default_factory=list)
    subfolders: List["NextcloudFolder"] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


class NextcloudConnector:
    """
    Connector do Nextcloud
    Przechowywanie załączników e-Doręczeń w chmurze
    
    Struktura folderów:
    /e-Doreczenia/
    ├── INBOX/
    │   ├── 2024-01/
    │   │   ├── msg-abc123/
    │   │   │   ├── attachment1.pdf
    │   │   │   └── attachment2.docx
    │   │   └── msg-def456/
    │   └── 2024-02/
    ├── SENT/
    └── ARCHIVE/
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        base_folder: Optional[str] = None
    ):
        self.url = url or os.getenv("NEXTCLOUD_URL", "http://localhost:8080")
        self.username = username or os.getenv("NEXTCLOUD_USER", "admin")
        self.password = password or os.getenv("NEXTCLOUD_PASSWORD", "admin")
        self.base_folder = base_folder or os.getenv("NEXTCLOUD_FOLDER", "/e-Doreczenia")
        
        self._connected = False
        self._webdav_url = f"{self.url}/remote.php/dav/files/{self.username}"
        
        # In-memory storage (demo)
        self._files: Dict[str, NextcloudFile] = {}
        self._folders: Dict[str, NextcloudFolder] = {}
        
        self._init_default_structure()
    
    def _init_default_structure(self):
        """Inicjalizuj domyślną strukturę folderów"""
        default_folders = [
            f"{self.base_folder}",
            f"{self.base_folder}/INBOX",
            f"{self.base_folder}/SENT",
            f"{self.base_folder}/DRAFTS",
            f"{self.base_folder}/ARCHIVE",
            f"{self.base_folder}/TRASH",
        ]
        
        for folder_path in default_folders:
            name = folder_path.split("/")[-1] or "e-Doreczenia"
            self._folders[folder_path] = NextcloudFolder(name=name, path=folder_path)
    
    # ═══════════════════════════════════════════════════════════════
    # CONNECTION
    # ═══════════════════════════════════════════════════════════════
    
    def connect(self) -> bool:
        """
        Połącz z Nextcloud
        
        Returns:
            True jeśli połączono pomyślnie
        """
        logger.info(f"Connecting to Nextcloud: {self.url}")
        
        # W produkcji: test połączenia WebDAV
        # import requests
        # response = requests.request(
        #     "PROPFIND",
        #     self._webdav_url,
        #     auth=(self.username, self.password)
        # )
        
        self._connected = True
        logger.info("Nextcloud connected")
        return True
    
    def disconnect(self) -> bool:
        """Rozłącz z Nextcloud"""
        self._connected = False
        return True
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    # ═══════════════════════════════════════════════════════════════
    # FOLDERS
    # ═══════════════════════════════════════════════════════════════
    
    def create_folder(self, folder_path: str) -> NextcloudFolder:
        """
        Utwórz folder
        
        Args:
            folder_path: Ścieżka folderu (względna do base_folder)
        
        Returns:
            Utworzony folder
        """
        full_path = f"{self.base_folder}/{folder_path}".replace("//", "/")
        
        if full_path in self._folders:
            return self._folders[full_path]
        
        name = folder_path.split("/")[-1]
        folder = NextcloudFolder(name=name, path=full_path)
        self._folders[full_path] = folder
        
        logger.info(f"Created folder: {full_path}")
        return folder
    
    def create_message_folder(self, message_id: str, folder_type: str = "INBOX") -> NextcloudFolder:
        """
        Utwórz folder dla wiadomości e-Doręczeń
        
        Args:
            message_id: ID wiadomości
            folder_type: Typ folderu (INBOX, SENT, etc.)
        
        Returns:
            Folder dla wiadomości
        """
        # Struktura: /e-Doreczenia/INBOX/2024-01/msg-abc123/
        date_folder = datetime.utcnow().strftime("%Y-%m")
        folder_path = f"{folder_type}/{date_folder}/{message_id}"
        
        return self.create_folder(folder_path)
    
    def list_folders(self, path: Optional[str] = None) -> List[NextcloudFolder]:
        """Lista folderów"""
        base = path or self.base_folder
        return [f for f in self._folders.values() if f.path.startswith(base)]
    
    def delete_folder(self, folder_path: str) -> bool:
        """Usuń folder"""
        full_path = f"{self.base_folder}/{folder_path}".replace("//", "/")
        
        if full_path in self._folders:
            del self._folders[full_path]
            return True
        return False
    
    # ═══════════════════════════════════════════════════════════════
    # FILES / ATTACHMENTS
    # ═══════════════════════════════════════════════════════════════
    
    def upload_attachment(
        self,
        message_id: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        folder_type: str = "INBOX"
    ) -> NextcloudFile:
        """
        Prześlij załącznik do Nextcloud
        
        Args:
            message_id: ID wiadomości e-Doręczeń
            filename: Nazwa pliku
            content: Zawartość pliku
            content_type: Typ MIME
            folder_type: Typ folderu (INBOX, SENT, etc.)
        
        Returns:
            Metadane przesłanego pliku
        """
        if not self._connected:
            raise RuntimeError("Not connected to Nextcloud")
        
        # Utwórz folder dla wiadomości
        msg_folder = self.create_message_folder(message_id, folder_type)
        
        # Generuj ID pliku
        file_id = hashlib.md5(f"{message_id}/{filename}".encode()).hexdigest()[:12]
        file_path = f"{msg_folder.path}/{filename}"
        
        nc_file = NextcloudFile(
            id=file_id,
            name=filename,
            path=file_path,
            size=len(content),
            content_type=content_type,
            etag=hashlib.md5(content).hexdigest(),
            modified_at=datetime.utcnow(),
            ade_message_id=message_id
        )
        
        self._files[file_path] = nc_file
        
        # W produkcji: upload przez WebDAV
        # response = requests.put(
        #     f"{self._webdav_url}{file_path}",
        #     data=content,
        #     auth=(self.username, self.password),
        #     headers={"Content-Type": content_type}
        # )
        
        logger.info(f"Uploaded attachment: {file_path} ({len(content)} bytes)")
        return nc_file
    
    def download_attachment(
        self,
        message_id: str,
        filename: str,
        folder_type: str = "INBOX"
    ) -> Optional[bytes]:
        """
        Pobierz załącznik z Nextcloud
        
        Args:
            message_id: ID wiadomości e-Doręczeń
            filename: Nazwa pliku
            folder_type: Typ folderu
        
        Returns:
            Zawartość pliku lub None
        """
        if not self._connected:
            raise RuntimeError("Not connected to Nextcloud")
        
        date_folder = datetime.utcnow().strftime("%Y-%m")
        file_path = f"{self.base_folder}/{folder_type}/{date_folder}/{message_id}/{filename}"
        
        # W produkcji: download przez WebDAV
        # response = requests.get(
        #     f"{self._webdav_url}{file_path}",
        #     auth=(self.username, self.password)
        # )
        # return response.content
        
        logger.info(f"Downloaded attachment: {file_path}")
        return None  # Demo: brak rzeczywistej zawartości
    
    def list_attachments(self, message_id: str, folder_type: str = "INBOX") -> List[NextcloudFile]:
        """
        Lista załączników dla wiadomości
        
        Args:
            message_id: ID wiadomości e-Doręczeń
            folder_type: Typ folderu
        
        Returns:
            Lista plików
        """
        return [f for f in self._files.values() if f.ade_message_id == message_id]
    
    def delete_attachment(self, message_id: str, filename: str) -> bool:
        """Usuń załącznik"""
        for path, file in list(self._files.items()):
            if file.ade_message_id == message_id and file.name == filename:
                del self._files[path]
                return True
        return False
    
    def move_attachments(
        self,
        message_id: str,
        from_folder: str,
        to_folder: str
    ) -> bool:
        """
        Przenieś załączniki do innego folderu
        
        Args:
            message_id: ID wiadomości
            from_folder: Folder źródłowy
            to_folder: Folder docelowy
        
        Returns:
            True jeśli przeniesiono
        """
        # Znajdź pliki do przeniesienia
        files_to_move = [f for f in self._files.values() 
                        if f.ade_message_id == message_id and from_folder in f.path]
        
        for file in files_to_move:
            new_path = file.path.replace(from_folder, to_folder)
            
            # Utwórz folder docelowy
            self.create_message_folder(message_id, to_folder)
            
            # Przenieś plik
            del self._files[file.path]
            file.path = new_path
            self._files[new_path] = file
        
        return len(files_to_move) > 0
    
    # ═══════════════════════════════════════════════════════════════
    # SHARING
    # ═══════════════════════════════════════════════════════════════
    
    def create_share_link(
        self,
        message_id: str,
        filename: Optional[str] = None,
        password: Optional[str] = None,
        expire_days: int = 7
    ) -> str:
        """
        Utwórz link do udostępnienia załącznika
        
        Args:
            message_id: ID wiadomości
            filename: Nazwa pliku (None = cały folder)
            password: Hasło do linku
            expire_days: Dni ważności
        
        Returns:
            URL do udostępnienia
        """
        import uuid
        share_token = uuid.uuid4().hex[:16]
        
        # W produkcji: Nextcloud Share API
        share_url = f"{self.url}/s/{share_token}"
        
        logger.info(f"Created share link: {share_url}")
        return share_url
    
    # ═══════════════════════════════════════════════════════════════
    # SYNC
    # ═══════════════════════════════════════════════════════════════
    
    def sync_message_attachments(
        self,
        message_id: str,
        attachments: List[Dict[str, Any]],
        folder_type: str = "INBOX"
    ) -> List[NextcloudFile]:
        """
        Synchronizuj załączniki wiadomości z Nextcloud
        
        Args:
            message_id: ID wiadomości e-Doręczeń
            attachments: Lista załączników z API e-Doręczeń
            folder_type: Typ folderu
        
        Returns:
            Lista zsynchronizowanych plików
        """
        synced_files = []
        
        for att in attachments:
            # Sprawdź czy plik już istnieje
            existing = [f for f in self._files.values() 
                       if f.ade_message_id == message_id and f.name == att.get("filename")]
            
            if existing:
                synced_files.append(existing[0])
                continue
            
            # Pobierz i prześlij załącznik
            # W produkcji: pobierz z API e-Doręczeń
            content = att.get("content", b"")
            if isinstance(content, str):
                content = base64.b64decode(content)
            
            nc_file = self.upload_attachment(
                message_id=message_id,
                filename=att.get("filename", "attachment"),
                content=content,
                content_type=att.get("content_type", "application/octet-stream"),
                folder_type=folder_type
            )
            synced_files.append(nc_file)
        
        return synced_files
    
    # ═══════════════════════════════════════════════════════════════
    # STATUS
    # ═══════════════════════════════════════════════════════════════
    
    def get_status(self) -> Dict[str, Any]:
        """Pobierz status połączenia"""
        return {
            "connected": self._connected,
            "url": self.url,
            "username": self.username,
            "base_folder": self.base_folder,
            "folders_count": len(self._folders),
            "files_count": len(self._files),
            "total_size": sum(f.size for f in self._files.values())
        }
    
    def get_quota(self) -> Dict[str, Any]:
        """Pobierz informacje o przestrzeni"""
        # W produkcji: Nextcloud API
        return {
            "used": sum(f.size for f in self._files.values()),
            "total": 10 * 1024 * 1024 * 1024,  # 10 GB
            "free": 10 * 1024 * 1024 * 1024 - sum(f.size for f in self._files.values())
        }
