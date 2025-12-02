#!/usr/bin/env python3
"""
Szyfromat.pl <-> Nextcloud Sync Service
Synchronizuje załączniki e-Doręczeń z Nextcloud
"""

import os
import time
import logging
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any

import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("szyfromat-sync")

# Configuration
NEXTCLOUD_URL = os.getenv("NEXTCLOUD_URL", "http://nextcloud")
NEXTCLOUD_USER = os.getenv("NEXTCLOUD_USER", "admin")
NEXTCLOUD_PASSWORD = os.getenv("NEXTCLOUD_PASSWORD", "admin")
SZYFROMAT_API_URL = os.getenv("SZYFROMAT_API_URL", "http://localhost:8500")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", "300"))
BASE_FOLDER = os.getenv("SZYFROMAT_BASE_FOLDER", "/e-Doreczenia")


class NextcloudClient:
    """Simple Nextcloud WebDAV client"""
    
    def __init__(self, url: str, username: str, password: str):
        self.url = url
        self.username = username
        self.password = password
        self.webdav_url = f"{url}/remote.php/dav/files/{username}"
        self.session = requests.Session()
        self.session.auth = (username, password)
    
    def create_folder(self, path: str) -> bool:
        """Create folder via WebDAV MKCOL"""
        try:
            response = self.session.request(
                "MKCOL",
                f"{self.webdav_url}{path}",
                timeout=30
            )
            return response.status_code in [201, 405]  # 405 = already exists
        except Exception as e:
            logger.error(f"Failed to create folder {path}: {e}")
            return False
    
    def upload_file(self, path: str, content: bytes, content_type: str = "application/octet-stream") -> bool:
        """Upload file via WebDAV PUT"""
        try:
            response = self.session.put(
                f"{self.webdav_url}{path}",
                data=content,
                headers={"Content-Type": content_type},
                timeout=60
            )
            return response.status_code in [200, 201, 204]
        except Exception as e:
            logger.error(f"Failed to upload file {path}: {e}")
            return False
    
    def download_file(self, path: str) -> Optional[bytes]:
        """Download file via WebDAV GET"""
        try:
            response = self.session.get(
                f"{self.webdav_url}{path}",
                timeout=60
            )
            if response.status_code == 200:
                return response.content
            return None
        except Exception as e:
            logger.error(f"Failed to download file {path}: {e}")
            return None
    
    def file_exists(self, path: str) -> bool:
        """Check if file exists via WebDAV HEAD"""
        try:
            response = self.session.head(
                f"{self.webdav_url}{path}",
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def list_folder(self, path: str) -> List[str]:
        """List folder contents via WebDAV PROPFIND"""
        try:
            response = self.session.request(
                "PROPFIND",
                f"{self.webdav_url}{path}",
                headers={"Depth": "1"},
                timeout=30
            )
            # Parse XML response (simplified)
            # In production: use proper XML parsing
            return []
        except Exception as e:
            logger.error(f"Failed to list folder {path}: {e}")
            return []


class SzyfromatClient:
    """Szyfromat.pl API client"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.session = requests.Session()
        self.token: Optional[str] = None
    
    def login(self, username: str, password: str) -> bool:
        """Login to Szyfromat.pl"""
        try:
            response = self.session.post(
                f"{self.api_url}/api/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.session.headers["Authorization"] = f"Bearer {self.token}"
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to login: {e}")
            return False
    
    def get_messages(self, folder: str = "inbox", limit: int = 50) -> List[Dict]:
        """Get messages from Szyfromat.pl"""
        try:
            response = self.session.get(
                f"{self.api_url}/api/messages",
                params={"folder": folder, "limit": limit},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("messages", [])
            return []
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    def get_attachment(self, message_id: str, attachment_id: str) -> Optional[bytes]:
        """Download attachment from Szyfromat.pl"""
        try:
            response = self.session.get(
                f"{self.api_url}/api/messages/{message_id}/attachments/{attachment_id}",
                timeout=60
            )
            if response.status_code == 200:
                return response.content
            return None
        except Exception as e:
            logger.error(f"Failed to get attachment: {e}")
            return None
    
    def health_check(self) -> bool:
        """Check if Szyfromat.pl API is available"""
        try:
            response = self.session.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False


class SyncService:
    """Main sync service"""
    
    def __init__(self):
        self.nextcloud = NextcloudClient(NEXTCLOUD_URL, NEXTCLOUD_USER, NEXTCLOUD_PASSWORD)
        self.szyfromat = SzyfromatClient(SZYFROMAT_API_URL)
        self.synced_files: set = set()
    
    def init_folders(self):
        """Initialize default folder structure"""
        folders = [
            BASE_FOLDER,
            f"{BASE_FOLDER}/INBOX",
            f"{BASE_FOLDER}/SENT",
            f"{BASE_FOLDER}/DRAFTS",
            f"{BASE_FOLDER}/ARCHIVE",
            f"{BASE_FOLDER}/TRASH",
        ]
        
        for folder in folders:
            if self.nextcloud.create_folder(folder):
                logger.info(f"Created folder: {folder}")
    
    def sync_message_attachments(self, message: Dict) -> int:
        """Sync attachments for a single message"""
        message_id = message.get("id", "unknown")
        attachments = message.get("attachments", [])
        folder_type = "SENT" if message.get("is_sent") else "INBOX"
        
        if not attachments:
            return 0
        
        # Create message folder
        date_folder = datetime.utcnow().strftime("%Y-%m")
        msg_folder = f"{BASE_FOLDER}/{folder_type}/{date_folder}/{message_id}"
        self.nextcloud.create_folder(f"{BASE_FOLDER}/{folder_type}/{date_folder}")
        self.nextcloud.create_folder(msg_folder)
        
        synced = 0
        for att in attachments:
            att_id = att.get("id", "")
            filename = att.get("filename", "attachment")
            file_path = f"{msg_folder}/{filename}"
            
            # Check if already synced
            file_key = f"{message_id}/{att_id}"
            if file_key in self.synced_files:
                continue
            
            # Check if file exists in Nextcloud
            if self.nextcloud.file_exists(file_path):
                self.synced_files.add(file_key)
                continue
            
            # Download from Szyfromat.pl
            content = self.szyfromat.get_attachment(message_id, att_id)
            if content:
                # Upload to Nextcloud
                if self.nextcloud.upload_file(
                    file_path,
                    content,
                    att.get("content_type", "application/octet-stream")
                ):
                    logger.info(f"Synced: {file_path}")
                    self.synced_files.add(file_key)
                    synced += 1
        
        return synced
    
    def sync_all(self):
        """Sync all messages"""
        logger.info("Starting sync...")
        
        total_synced = 0
        
        # Sync inbox
        messages = self.szyfromat.get_messages("inbox", limit=100)
        for msg in messages:
            total_synced += self.sync_message_attachments(msg)
        
        # Sync sent
        messages = self.szyfromat.get_messages("sent", limit=100)
        for msg in messages:
            msg["is_sent"] = True
            total_synced += self.sync_message_attachments(msg)
        
        logger.info(f"Sync completed. Files synced: {total_synced}")
    
    def run(self):
        """Main loop"""
        logger.info("=" * 60)
        logger.info("Szyfromat.pl <-> Nextcloud Sync Service")
        logger.info("=" * 60)
        logger.info(f"Nextcloud URL: {NEXTCLOUD_URL}")
        logger.info(f"Szyfromat API: {SZYFROMAT_API_URL}")
        logger.info(f"Sync interval: {SYNC_INTERVAL}s")
        logger.info(f"Base folder: {BASE_FOLDER}")
        logger.info("=" * 60)
        
        # Wait for services to be ready
        logger.info("Waiting for services...")
        time.sleep(10)
        
        # Initialize folders
        self.init_folders()
        
        # Main loop
        while True:
            try:
                # Check Szyfromat.pl availability
                if not self.szyfromat.health_check():
                    logger.warning("Szyfromat.pl API not available, retrying...")
                    time.sleep(30)
                    continue
                
                # Sync
                self.sync_all()
                
            except Exception as e:
                logger.error(f"Sync error: {e}")
            
            # Wait for next sync
            logger.info(f"Next sync in {SYNC_INTERVAL}s...")
            time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    service = SyncService()
    service.run()
