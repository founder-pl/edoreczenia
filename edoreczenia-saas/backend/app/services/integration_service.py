"""
Integration Service - Obsługa integracji adresów z SQLite
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from ..database import SessionLocal, AddressIntegration, User


class IntegrationService:
    """Serwis do obsługi integracji adresów e-Doręczeń"""
    
    def __init__(self):
        pass
    
    def _get_db(self) -> Session:
        return SessionLocal()
    
    def create_integration(
        self,
        user_id: str,
        ade_address: str,
        provider: str = "certum",
        auth_method: str = "mobywatel",
        entity_type: str = "person",
        nip: str = None,
        pesel: str = None,
        krs: str = None,
        regon: str = None
    ) -> AddressIntegration:
        """Utwórz nową integrację"""
        db = self._get_db()
        try:
            integration = AddressIntegration(
                id=f"int-{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                ade_address=ade_address,
                status="pending",
                provider=provider,
                auth_method=auth_method,
                entity_type=entity_type,
                nip=nip,
                pesel=pesel,
                krs=krs,
                regon=regon,
                message="Oczekuje na weryfikację",
                created_at=datetime.utcnow()
            )
            db.add(integration)
            db.commit()
            db.refresh(integration)
            return integration
        finally:
            db.close()
    
    def get_integrations(self, user_id: str) -> List[AddressIntegration]:
        """Pobierz integracje użytkownika"""
        db = self._get_db()
        try:
            return db.query(AddressIntegration).filter(
                AddressIntegration.user_id == user_id
            ).order_by(AddressIntegration.created_at.desc()).all()
        finally:
            db.close()
    
    def get_integration(self, integration_id: str) -> Optional[AddressIntegration]:
        """Pobierz szczegóły integracji"""
        db = self._get_db()
        try:
            return db.query(AddressIntegration).filter(
                AddressIntegration.id == integration_id
            ).first()
        finally:
            db.close()
    
    def start_verification(self, integration_id: str) -> AddressIntegration:
        """Rozpocznij weryfikację"""
        db = self._get_db()
        try:
            integration = db.query(AddressIntegration).filter(
                AddressIntegration.id == integration_id
            ).first()
            
            if integration:
                integration.status = "verifying"
                integration.message = "Trwa weryfikacja tożsamości..."
                db.commit()
                db.refresh(integration)
            
            return integration
        finally:
            db.close()
    
    def complete_verification(self, integration_id: str) -> AddressIntegration:
        """Zakończ weryfikację pomyślnie"""
        db = self._get_db()
        try:
            integration = db.query(AddressIntegration).filter(
                AddressIntegration.id == integration_id
            ).first()
            
            if integration:
                integration.status = "active"
                integration.verified_at = datetime.utcnow()
                integration.message = "Integracja zakończona pomyślnie"
                
                # Generuj poświadczenia
                integration.oauth_token = f"oauth_{uuid.uuid4().hex[:16]}"
                integration.certificate_thumbprint = f"cert_{uuid.uuid4().hex[:32]}"
                integration.api_key = f"api_{uuid.uuid4().hex[:24]}"
                integration.credentials_expire_at = datetime.utcnow() + timedelta(days=365)
                
                db.commit()
                db.refresh(integration)
            
            return integration
        finally:
            db.close()
    
    def fail_verification(self, integration_id: str, reason: str) -> AddressIntegration:
        """Oznacz weryfikację jako nieudaną"""
        db = self._get_db()
        try:
            integration = db.query(AddressIntegration).filter(
                AddressIntegration.id == integration_id
            ).first()
            
            if integration:
                integration.status = "failed"
                integration.message = reason
                db.commit()
                db.refresh(integration)
            
            return integration
        finally:
            db.close()
    
    def delete_integration(self, integration_id: str) -> bool:
        """Usuń integrację"""
        db = self._get_db()
        try:
            integration = db.query(AddressIntegration).filter(
                AddressIntegration.id == integration_id
            ).first()
            
            if integration:
                db.delete(integration)
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def get_credentials(self, integration_id: str) -> Optional[Dict[str, Any]]:
        """Pobierz poświadczenia integracji"""
        db = self._get_db()
        try:
            integration = db.query(AddressIntegration).filter(
                AddressIntegration.id == integration_id
            ).first()
            
            if integration and integration.status == "active":
                return {
                    "integration_id": integration.id,
                    "oauth_token": integration.oauth_token,
                    "certificate_thumbprint": integration.certificate_thumbprint,
                    "api_key": integration.api_key,
                    "expires_at": integration.credentials_expire_at.isoformat() if integration.credentials_expire_at else None
                }
            return None
        finally:
            db.close()
    
    def get_verification_steps(self, integration_id: str) -> List[Dict[str, Any]]:
        """Pobierz kroki weryfikacji"""
        db = self._get_db()
        try:
            integration = db.query(AddressIntegration).filter(
                AddressIntegration.id == integration_id
            ).first()
            
            if not integration:
                return []
            
            status = integration.status
            auth_method = integration.auth_method or "mobywatel"
            
            return [
                {
                    "step": 1,
                    "name": "Weryfikacja adresu ADE",
                    "status": "completed" if status != "pending" else "in_progress",
                    "description": "Sprawdzenie poprawności adresu w rejestrze e-Doręczeń",
                    "required_action": None
                },
                {
                    "step": 2,
                    "name": "Weryfikacja tożsamości",
                    "status": "completed" if status in ["active", "verifying"] else "pending",
                    "description": f"Uwierzytelnienie przez {auth_method}",
                    "required_action": "Zaloguj się przez wybraną metodę uwierzytelnienia" if status == "pending" else None
                },
                {
                    "step": 3,
                    "name": "Pobranie certyfikatu",
                    "status": "completed" if status == "active" else "pending",
                    "description": "Pobranie certyfikatu do podpisywania wiadomości",
                    "required_action": None
                },
                {
                    "step": 4,
                    "name": "Konfiguracja połączenia",
                    "status": "completed" if status == "active" else "pending",
                    "description": "Konfiguracja połączenia z serwerem e-Doręczeń",
                    "required_action": None
                },
                {
                    "step": 5,
                    "name": "Test połączenia",
                    "status": "completed" if status == "active" else "pending",
                    "description": "Weryfikacja poprawności konfiguracji",
                    "required_action": None
                }
            ]
        finally:
            db.close()
    
    def to_response_dict(self, integration: AddressIntegration) -> Dict[str, Any]:
        """Konwertuj na słownik odpowiedzi API"""
        return {
            "id": integration.id,
            "ade_address": integration.ade_address,
            "status": integration.status,
            "provider": integration.provider,
            "entity_type": integration.entity_type,
            "created_at": integration.created_at.isoformat() if integration.created_at else None,
            "verified_at": integration.verified_at.isoformat() if integration.verified_at else None,
            "message": integration.message
        }


# Singleton instance
integration_service = IntegrationService()
