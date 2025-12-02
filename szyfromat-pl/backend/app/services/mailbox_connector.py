"""
Mailbox Connector - Łączenie istniejących skrzynek e-Doręczeń z SaaS

Obsługuje różne metody integracji:
1. OAuth2 - przez oficjalne API e-Doręczeń
2. Certyfikat kwalifikowany - podpis elektroniczny
3. mObywatel - uwierzytelnienie przez aplikację
4. API Key - dla systemów zewnętrznych
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
import uuid
import hashlib
import base64

from sqlalchemy.orm import Session
from ..database import SessionLocal, MailboxConnection


class ConnectionMethod(str, Enum):
    """Metody połączenia ze skrzynką"""
    OAUTH2 = "oauth2"
    CERTIFICATE = "certificate"
    MOBYWATEL = "mobywatel"
    API_KEY = "api_key"
    PROXY = "proxy"


class ConnectionStatus(str, Enum):
    """Status połączenia"""
    PENDING = "pending"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ACTIVE = "active"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class MailboxConnectorService:
    """Serwis do zarządzania połączeniami ze skrzynkami"""
    
    # Oficjalne endpointy e-Doręczeń (produkcyjne)
    EDORECZENIA_AUTH_URL = "https://edoreczenia.gov.pl/oauth/authorize"
    EDORECZENIA_TOKEN_URL = "https://edoreczenia.gov.pl/oauth/token"
    EDORECZENIA_API_URL = "https://edoreczenia.gov.pl/api/v1"
    
    # Testowe endpointy
    EDORECZENIA_TEST_AUTH_URL = "https://test.edoreczenia.gov.pl/oauth/authorize"
    EDORECZENIA_TEST_TOKEN_URL = "https://test.edoreczenia.gov.pl/oauth/token"
    EDORECZENIA_TEST_API_URL = "https://test.edoreczenia.gov.pl/api/v1"
    
    def __init__(self):
        self.use_test_env = True  # Domyślnie środowisko testowe
    
    def _get_db(self) -> Session:
        return SessionLocal()
    
    # ═══════════════════════════════════════════════════════════════
    # TWORZENIE POŁĄCZENIA
    # ═══════════════════════════════════════════════════════════════
    
    def create_connection(
        self,
        user_id: str,
        ade_address: str,
        connection_method: str = "oauth2",
        mailbox_name: str = None,
        mailbox_type: str = "person"
    ) -> MailboxConnection:
        """Utwórz nowe połączenie ze skrzynką"""
        db = self._get_db()
        try:
            # Sprawdź czy połączenie już istnieje
            existing = db.query(MailboxConnection).filter(
                MailboxConnection.ade_address == ade_address
            ).first()
            
            if existing:
                raise ValueError(f"Skrzynka {ade_address} jest już połączona")
            
            connection = MailboxConnection(
                id=f"conn-{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                ade_address=ade_address,
                mailbox_name=mailbox_name or ade_address,
                mailbox_type=mailbox_type,
                connection_method=connection_method,
                status=ConnectionStatus.PENDING.value,
                created_at=datetime.utcnow()
            )
            
            db.add(connection)
            db.commit()
            db.refresh(connection)
            return connection
        finally:
            db.close()
    
    # ═══════════════════════════════════════════════════════════════
    # OAUTH2 - Oficjalne API e-Doręczeń
    # ═══════════════════════════════════════════════════════════════
    
    def get_oauth_authorization_url(
        self,
        connection_id: str,
        redirect_uri: str,
        scope: str = "messages.read messages.write"
    ) -> Dict[str, str]:
        """Generuj URL do autoryzacji OAuth2"""
        state = hashlib.sha256(f"{connection_id}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:32]
        
        auth_url = self.EDORECZENIA_TEST_AUTH_URL if self.use_test_env else self.EDORECZENIA_AUTH_URL
        
        params = {
            "response_type": "code",
            "client_id": "${EDORECZENIA_CLIENT_ID}",  # Z konfiguracji
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state
        }
        
        query = "&".join(f"{k}={v}" for k, v in params.items())
        
        return {
            "authorization_url": f"{auth_url}?{query}",
            "state": state,
            "instructions": [
                "1. Otwórz powyższy URL w przeglądarce",
                "2. Zaloguj się do systemu e-Doręczeń",
                "3. Wyraź zgodę na dostęp aplikacji",
                "4. Zostaniesz przekierowany z kodem autoryzacji"
            ]
        }
    
    def complete_oauth_authorization(
        self,
        connection_id: str,
        authorization_code: str
    ) -> MailboxConnection:
        """Zakończ autoryzację OAuth2 - wymień kod na tokeny"""
        db = self._get_db()
        try:
            connection = db.query(MailboxConnection).filter(
                MailboxConnection.id == connection_id
            ).first()
            
            if not connection:
                raise ValueError("Połączenie nie znalezione")
            
            # W produkcji: wywołaj API e-Doręczeń aby wymienić kod na tokeny
            # Tutaj symulacja:
            connection.oauth_access_token = f"access_{uuid.uuid4().hex}"
            connection.oauth_refresh_token = f"refresh_{uuid.uuid4().hex}"
            connection.oauth_expires_at = datetime.utcnow() + timedelta(hours=1)
            connection.status = ConnectionStatus.CONNECTED.value
            connection.connected_at = datetime.utcnow()
            
            db.commit()
            db.refresh(connection)
            return connection
        finally:
            db.close()
    
    # ═══════════════════════════════════════════════════════════════
    # CERTYFIKAT KWALIFIKOWANY
    # ═══════════════════════════════════════════════════════════════
    
    def connect_with_certificate(
        self,
        connection_id: str,
        certificate_data: str,  # Base64 encoded certificate
        certificate_password: str = None
    ) -> Dict[str, Any]:
        """Połącz używając certyfikatu kwalifikowanego"""
        db = self._get_db()
        try:
            connection = db.query(MailboxConnection).filter(
                MailboxConnection.id == connection_id
            ).first()
            
            if not connection:
                raise ValueError("Połączenie nie znalezione")
            
            # W produkcji: walidacja certyfikatu
            # Tutaj symulacja:
            cert_thumbprint = hashlib.sha256(certificate_data.encode()).hexdigest()[:40]
            
            connection.certificate_thumbprint = cert_thumbprint
            connection.certificate_subject = "CN=Użytkownik, O=Organizacja"
            connection.certificate_expires_at = datetime.utcnow() + timedelta(days=365)
            connection.connection_method = ConnectionMethod.CERTIFICATE.value
            connection.status = ConnectionStatus.CONNECTED.value
            connection.connected_at = datetime.utcnow()
            
            db.commit()
            
            return {
                "status": "connected",
                "certificate_thumbprint": cert_thumbprint,
                "expires_at": connection.certificate_expires_at.isoformat()
            }
        finally:
            db.close()
    
    # ═══════════════════════════════════════════════════════════════
    # mOBYWATEL
    # ═══════════════════════════════════════════════════════════════
    
    def initiate_mobywatel_auth(self, connection_id: str) -> Dict[str, Any]:
        """Rozpocznij uwierzytelnienie przez mObywatel"""
        db = self._get_db()
        try:
            connection = db.query(MailboxConnection).filter(
                MailboxConnection.id == connection_id
            ).first()
            
            if not connection:
                raise ValueError("Połączenie nie znalezione")
            
            # Generuj kod QR / deep link do mObywatel
            auth_code = uuid.uuid4().hex[:8].upper()
            
            connection.connection_method = ConnectionMethod.MOBYWATEL.value
            connection.status = ConnectionStatus.CONNECTING.value
            connection.extra_config = {
                "mobywatel_auth_code": auth_code,
                "mobywatel_auth_expires": (datetime.utcnow() + timedelta(minutes=10)).isoformat()
            }
            
            db.commit()
            
            return {
                "auth_code": auth_code,
                "qr_code_url": f"https://mobywatel.gov.pl/auth?code={auth_code}",
                "deep_link": f"mobywatel://auth?code={auth_code}&app=edoreczenia-saas",
                "expires_in_seconds": 600,
                "instructions": [
                    "1. Otwórz aplikację mObywatel na telefonie",
                    "2. Wybierz 'Potwierdź tożsamość'",
                    f"3. Wprowadź kod: {auth_code}",
                    "4. Potwierdź swoją tożsamość"
                ]
            }
        finally:
            db.close()
    
    def verify_mobywatel_auth(self, connection_id: str, verification_code: str) -> MailboxConnection:
        """Zweryfikuj uwierzytelnienie mObywatel"""
        db = self._get_db()
        try:
            connection = db.query(MailboxConnection).filter(
                MailboxConnection.id == connection_id
            ).first()
            
            if not connection:
                raise ValueError("Połączenie nie znalezione")
            
            # W produkcji: weryfikacja z API mObywatel
            # Tutaj symulacja sukcesu:
            connection.status = ConnectionStatus.CONNECTED.value
            connection.connected_at = datetime.utcnow()
            connection.oauth_access_token = f"mobywatel_{uuid.uuid4().hex}"
            connection.oauth_expires_at = datetime.utcnow() + timedelta(days=30)
            
            db.commit()
            db.refresh(connection)
            return connection
        finally:
            db.close()
    
    # ═══════════════════════════════════════════════════════════════
    # API KEY - dla systemów zewnętrznych
    # ═══════════════════════════════════════════════════════════════
    
    def generate_api_credentials(self, connection_id: str) -> Dict[str, str]:
        """Generuj klucz API dla połączenia"""
        db = self._get_db()
        try:
            connection = db.query(MailboxConnection).filter(
                MailboxConnection.id == connection_id
            ).first()
            
            if not connection:
                raise ValueError("Połączenie nie znalezione")
            
            # Generuj klucz i sekret
            api_key = f"edor_{uuid.uuid4().hex[:16]}"
            api_secret = uuid.uuid4().hex + uuid.uuid4().hex[:16]
            
            connection.api_key = api_key
            connection.api_secret_hash = hashlib.sha256(api_secret.encode()).hexdigest()
            connection.connection_method = ConnectionMethod.API_KEY.value
            connection.status = ConnectionStatus.CONNECTED.value
            connection.connected_at = datetime.utcnow()
            
            db.commit()
            
            return {
                "api_key": api_key,
                "api_secret": api_secret,  # Pokaż tylko raz!
                "warning": "Zapisz api_secret - nie będzie można go odzyskać!",
                "usage": {
                    "header": "Authorization: Bearer <api_key>:<api_secret>",
                    "example": f"Authorization: Bearer {api_key}:{api_secret[:8]}..."
                }
            }
        finally:
            db.close()
    
    # ═══════════════════════════════════════════════════════════════
    # SYNCHRONIZACJA
    # ═══════════════════════════════════════════════════════════════
    
    def start_sync(self, connection_id: str) -> Dict[str, Any]:
        """Rozpocznij synchronizację skrzynki"""
        db = self._get_db()
        try:
            connection = db.query(MailboxConnection).filter(
                MailboxConnection.id == connection_id
            ).first()
            
            if not connection:
                raise ValueError("Połączenie nie znalezione")
            
            if connection.status != ConnectionStatus.CONNECTED.value and \
               connection.status != ConnectionStatus.ACTIVE.value:
                raise ValueError("Skrzynka nie jest połączona")
            
            connection.status = ConnectionStatus.SYNCING.value
            connection.last_sync_at = datetime.utcnow()
            
            db.commit()
            
            # W produkcji: uruchom zadanie synchronizacji w tle
            # Tutaj symulacja:
            return {
                "status": "syncing",
                "started_at": connection.last_sync_at.isoformat(),
                "message": "Synchronizacja rozpoczęta"
            }
        finally:
            db.close()
    
    def complete_sync(self, connection_id: str, messages_count: int = 0) -> MailboxConnection:
        """Zakończ synchronizację"""
        db = self._get_db()
        try:
            connection = db.query(MailboxConnection).filter(
                MailboxConnection.id == connection_id
            ).first()
            
            if not connection:
                raise ValueError("Połączenie nie znalezione")
            
            connection.status = ConnectionStatus.ACTIVE.value
            connection.messages_synced = (connection.messages_synced or 0) + messages_count
            connection.next_sync_at = datetime.utcnow() + timedelta(minutes=connection.sync_interval_minutes or 5)
            connection.last_error = None
            
            db.commit()
            db.refresh(connection)
            return connection
        finally:
            db.close()
    
    # ═══════════════════════════════════════════════════════════════
    # ZARZĄDZANIE POŁĄCZENIAMI
    # ═══════════════════════════════════════════════════════════════
    
    def get_connections(self, user_id: str) -> List[MailboxConnection]:
        """Pobierz wszystkie połączenia użytkownika"""
        db = self._get_db()
        try:
            return db.query(MailboxConnection).filter(
                MailboxConnection.user_id == user_id
            ).order_by(MailboxConnection.created_at.desc()).all()
        finally:
            db.close()
    
    def get_connection(self, connection_id: str) -> Optional[MailboxConnection]:
        """Pobierz połączenie"""
        db = self._get_db()
        try:
            return db.query(MailboxConnection).filter(
                MailboxConnection.id == connection_id
            ).first()
        finally:
            db.close()
    
    def disconnect(self, connection_id: str) -> bool:
        """Rozłącz skrzynkę"""
        db = self._get_db()
        try:
            connection = db.query(MailboxConnection).filter(
                MailboxConnection.id == connection_id
            ).first()
            
            if not connection:
                return False
            
            # Wyczyść dane uwierzytelniające
            connection.oauth_access_token = None
            connection.oauth_refresh_token = None
            connection.api_key = None
            connection.api_secret_hash = None
            connection.status = ConnectionStatus.DISCONNECTED.value
            connection.sync_enabled = False
            
            db.commit()
            return True
        finally:
            db.close()
    
    def delete_connection(self, connection_id: str) -> bool:
        """Usuń połączenie"""
        db = self._get_db()
        try:
            connection = db.query(MailboxConnection).filter(
                MailboxConnection.id == connection_id
            ).first()
            
            if connection:
                db.delete(connection)
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def to_response_dict(self, connection: MailboxConnection) -> Dict[str, Any]:
        """Konwertuj na słownik odpowiedzi API"""
        return {
            "id": connection.id,
            "ade_address": connection.ade_address,
            "mailbox_name": connection.mailbox_name,
            "mailbox_type": connection.mailbox_type,
            "connection_method": connection.connection_method,
            "status": connection.status,
            "sync_enabled": connection.sync_enabled,
            "messages_synced": connection.messages_synced or 0,
            "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            "next_sync_at": connection.next_sync_at.isoformat() if connection.next_sync_at else None,
            "connected_at": connection.connected_at.isoformat() if connection.connected_at else None,
            "created_at": connection.created_at.isoformat() if connection.created_at else None,
            "last_error": connection.last_error
        }


# Singleton
mailbox_connector = MailboxConnectorService()
