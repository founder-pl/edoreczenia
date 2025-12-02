"""
e-Doręczenia DSL - Python Client

Klient API e-Doręczeń z pełnym wsparciem DSL.
"""

import json
import urllib.request
import urllib.parse
import base64
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from .config import config
from .logger import MarkdownLogger


class EDoreczeniaClient:
    """Klient DSL dla API e-Doręczeń"""
    
    def __init__(self, 
                 api_url: Optional[str] = None,
                 address: Optional[str] = None,
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 logger: Optional[MarkdownLogger] = None):
        
        self.api_url = api_url or config.api_url
        self.address = address or config.address
        self.client_id = client_id or config.client_id
        self.client_secret = client_secret or config.client_secret
        
        self.logger = logger or MarkdownLogger()
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
    
    def _request(self, method: str, endpoint: str, 
                 data: Optional[Dict] = None,
                 headers: Optional[Dict] = None,
                 auth: bool = True) -> Dict:
        """Wykonuje request HTTP"""
        url = f"{self.api_url}{endpoint}"
        
        req_headers = headers or {}
        if auth and self.access_token:
            req_headers['Authorization'] = f'Bearer {self.access_token}'
        
        body = None
        if data:
            if req_headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                body = urllib.parse.urlencode(data).encode()
            else:
                req_headers['Content-Type'] = 'application/json'
                body = json.dumps(data).encode()
        
        req = urllib.request.Request(url, data=body, method=method)
        for k, v in req_headers.items():
            req.add_header(k, v)
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                if content:
                    return json.loads(content)
                return {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else str(e)
            raise Exception(f"HTTP {e.code}: {error_body}")
    
    # ═══════════════════════════════════════════════════════════════
    # OAUTH2
    # ═══════════════════════════════════════════════════════════════
    
    def authenticate(self) -> str:
        """Pobiera token OAuth2"""
        self.logger.info('AUTH', f'Pobieranie tokenu OAuth2 z {self.api_url}')
        
        result = self._request(
            'POST', '/oauth/token',
            data={
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            auth=False
        )
        
        self.access_token = result['access_token']
        self.logger.success('AUTH', 'Token OAuth2 pobrany', {
            'token': self.access_token[:20] + '...',
            'expires_in': result.get('expires_in', 3600)
        })
        
        return self.access_token
    
    def ensure_authenticated(self):
        """Upewnia się, że klient jest uwierzytelniony"""
        if not self.access_token:
            self.authenticate()
    
    # ═══════════════════════════════════════════════════════════════
    # WIADOMOŚCI
    # ═══════════════════════════════════════════════════════════════
    
    def get_messages(self, folder: str = 'inbox', limit: int = 20, 
                     offset: int = 0) -> List[Dict]:
        """Pobiera listę wiadomości"""
        self.ensure_authenticated()
        self.logger.info('API', f'Pobieranie wiadomości z folderu: {folder}')
        
        result = self._request(
            'GET', 
            f'/ua/v5/{self.address}/messages?folder={folder}&limit={limit}&offset={offset}'
        )
        
        messages = result.get('messages', [])
        self.logger.success('API', f'Pobrano {len(messages)} wiadomości', {
            'folder': folder,
            'total': result.get('total', len(messages))
        })
        
        return messages
    
    def get_message(self, message_id: str) -> Dict:
        """Pobiera szczegóły wiadomości"""
        self.ensure_authenticated()
        self.logger.info('API', f'Pobieranie wiadomości: {message_id}')
        
        result = self._request('GET', f'/ua/v5/{self.address}/messages/{message_id}')
        
        msg = result[0] if isinstance(result, list) else result
        self.logger.success('API', f'Pobrano wiadomość: {msg.get("subject", "")[:40]}')
        
        return msg
    
    def send_message(self, recipient: str, subject: str, content: str,
                     attachments: Optional[List[Dict]] = None) -> Dict:
        """Wysyła wiadomość"""
        self.ensure_authenticated()
        self.logger.info('API', f'Wysyłanie wiadomości do: {recipient}')
        
        message = {
            'subject': subject,
            'recipients': [{'address': recipient, 'name': 'Odbiorca'}],
            'content': content,
            'attachments': attachments or []
        }
        
        result = self._request('POST', f'/ua/v5/{self.address}/messages', data=message)
        
        self.logger.success('API', f'Wiadomość wysłana', {
            'messageId': result.get('messageId'),
            'status': result.get('status')
        })
        
        return result
    
    def send_document(self, recipient: str, file_path: str, 
                      subject: Optional[str] = None) -> Dict:
        """Wysyła dokument jako załącznik"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Plik nie istnieje: {file_path}")
        
        self.logger.info('API', f'Wysyłanie dokumentu: {path.name}')
        
        # Określ MIME type
        mime_types = {
            '.pdf': 'application/pdf',
            '.xml': 'application/xml',
            '.txt': 'text/plain',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        mime_type = mime_types.get(path.suffix.lower(), 'application/octet-stream')
        
        # Przygotuj załącznik
        with open(path, 'rb') as f:
            content = base64.b64encode(f.read()).decode()
        
        attachment = {
            'filename': path.name,
            'contentType': mime_type,
            'content': content
        }
        
        return self.send_message(
            recipient=recipient,
            subject=subject or f'Dokument: {path.name}',
            content=f'W załączeniu przesyłam dokument: {path.name}',
            attachments=[attachment]
        )
    
    def delete_message(self, message_id: str) -> Dict:
        """Usuwa wiadomość"""
        self.ensure_authenticated()
        self.logger.info('API', f'Usuwanie wiadomości: {message_id}')
        
        result = self._request('DELETE', f'/ua/v5/{self.address}/messages/{message_id}')
        
        self.logger.success('API', f'Wiadomość usunięta: {message_id}')
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # KATALOGI
    # ═══════════════════════════════════════════════════════════════
    
    def get_directories(self) -> List[Dict]:
        """Pobiera listę katalogów"""
        self.ensure_authenticated()
        self.logger.info('API', 'Pobieranie katalogów')
        
        result = self._request('GET', f'/ua/v5/{self.address}/directories')
        
        directories = result.get('directories', [])
        self.logger.success('API', f'Pobrano {len(directories)} katalogów')
        
        return directories
    
    # ═══════════════════════════════════════════════════════════════
    # ZAŁĄCZNIKI
    # ═══════════════════════════════════════════════════════════════
    
    def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Pobiera załącznik"""
        self.ensure_authenticated()
        self.logger.info('API', f'Pobieranie załącznika: {attachment_id}')
        
        url = f"{self.api_url}/ua/v5/{self.address}/messages/{message_id}/attachments/{attachment_id}"
        
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {self.access_token}')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
        
        self.logger.success('API', f'Pobrano załącznik: {len(content)} bajtów')
        return content
    
    def download_attachment(self, message_id: str, attachment_id: str, 
                           filename: str, output_dir: str = '.') -> str:
        """Pobiera i zapisuje załącznik"""
        content = self.get_attachment(message_id, attachment_id)
        
        output_path = Path(output_dir) / filename
        with open(output_path, 'wb') as f:
            f.write(content)
        
        self.logger.success('API', f'Załącznik zapisany: {output_path}')
        return str(output_path)
    
    # ═══════════════════════════════════════════════════════════════
    # HEALTH CHECK
    # ═══════════════════════════════════════════════════════════════
    
    def health_check(self) -> Dict:
        """Sprawdza status API"""
        self.logger.info('API', f'Health check: {self.api_url}')
        
        result = self._request('GET', '/health', auth=False)
        
        self.logger.success('API', f'API healthy: {result.get("service")}', {
            'version': result.get('version'),
            'status': result.get('status')
        })
        
        return result
