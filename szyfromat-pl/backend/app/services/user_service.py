"""
User Service - Obsługa użytkowników z SQLite
"""

from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import hashlib
import uuid

from ..database import SessionLocal, User, Folder


class UserService:
    """Serwis do obsługi użytkowników"""
    
    def __init__(self):
        pass
    
    def _get_db(self) -> Session:
        return SessionLocal()
    
    def _hash_password(self, password: str) -> str:
        """Hash hasła (w produkcji użyć bcrypt)"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(
        self,
        username: str,
        password: str,
        email: str = None,
        name: str = None,
        ade_address: str = None
    ) -> User:
        """Utwórz nowego użytkownika"""
        db = self._get_db()
        try:
            user = User(
                id=f"user-{uuid.uuid4().hex[:8]}",
                username=username,
                password_hash=self._hash_password(password),
                email=email,
                name=name or username,
                ade_address=ade_address,
                created_at=datetime.utcnow()
            )
            db.add(user)
            
            # Utwórz domyślne foldery
            default_folders = [
                ("inbox", "Odebrane", "INBOX"),
                ("sent", "Wysłane", "SENT"),
                ("drafts", "Robocze", "DRAFTS"),
                ("trash", "Kosz", "TRASH"),
                ("archive", "Archiwum", "ARCHIVE"),
            ]
            for folder_id, name, label in default_folders:
                folder = Folder(
                    id=f"{folder_id}-{user.id}",
                    user_id=user.id,
                    name=name,
                    label=label,
                    is_system=True
                )
                db.add(folder)
            
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Uwierzytelnij użytkownika"""
        db = self._get_db()
        try:
            password_hash = self._hash_password(password)
            user = db.query(User).filter(
                User.username == username,
                User.password_hash == password_hash,
                User.is_active == True
            ).first()
            return user
        finally:
            db.close()
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Pobierz użytkownika po ID"""
        db = self._get_db()
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Pobierz użytkownika po nazwie"""
        db = self._get_db()
        try:
            return db.query(User).filter(User.username == username).first()
        finally:
            db.close()
    
    def update_user(
        self,
        user_id: str,
        email: str = None,
        name: str = None,
        ade_address: str = None
    ) -> Optional[User]:
        """Zaktualizuj dane użytkownika"""
        db = self._get_db()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                if email is not None:
                    user.email = email
                if name is not None:
                    user.name = name
                if ade_address is not None:
                    user.ade_address = ade_address
                user.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(user)
            return user
        finally:
            db.close()
    
    def change_password(self, user_id: str, new_password: str) -> bool:
        """Zmień hasło użytkownika"""
        db = self._get_db()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.password_hash = self._hash_password(new_password)
                user.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def deactivate_user(self, user_id: str) -> bool:
        """Dezaktywuj użytkownika"""
        db = self._get_db()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_active = False
                user.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def to_response_dict(self, user: User) -> Dict[str, Any]:
        """Konwertuj na słownik odpowiedzi API"""
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "address": user.ade_address,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }


# Singleton instance
user_service = UserService()
