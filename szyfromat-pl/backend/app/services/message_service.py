"""
Message Service - Obsługa wiadomości z SQLite
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid

from ..database import SessionLocal, Message, User, Folder


class MessageService:
    """Serwis do obsługi wiadomości"""
    
    def __init__(self):
        pass
    
    def _get_db(self) -> Session:
        return SessionLocal()
    
    def create_message(
        self,
        user_id: str,
        subject: str,
        content: str,
        recipient_address: str,
        recipient_name: str = None,
        folder: str = "drafts",
        status: str = "DRAFT"
    ) -> Message:
        """Utwórz nową wiadomość"""
        db = self._get_db()
        try:
            message = Message(
                id=f"msg-{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                folder=folder,
                subject=subject,
                content=content,
                status=status,
                sender_address=self._get_user_address(db, user_id),
                sender_name=self._get_user_name(db, user_id),
                recipient_address=recipient_address,
                recipient_name=recipient_name,
                created_at=datetime.utcnow()
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            return message
        finally:
            db.close()
    
    def _get_user_address(self, db: Session, user_id: str) -> str:
        user = db.query(User).filter(User.id == user_id).first()
        return user.ade_address if user else "unknown"
    
    def _get_user_name(self, db: Session, user_id: str) -> str:
        user = db.query(User).filter(User.id == user_id).first()
        return user.name if user else "Unknown"
    
    def send_message(self, message_id: str) -> Message:
        """Wyślij wiadomość (zmień status i folder)"""
        db = self._get_db()
        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if message:
                message.status = "SENT"
                message.folder = "sent"
                message.sent_at = datetime.utcnow()
                db.commit()
                db.refresh(message)
            return message
        finally:
            db.close()
    
    def get_messages(
        self,
        user_id: str,
        folder: str = "inbox",
        limit: int = 50,
        offset: int = 0,
        status: str = None
    ) -> List[Message]:
        """Pobierz wiadomości z folderu"""
        db = self._get_db()
        try:
            query = db.query(Message).filter(
                Message.user_id == user_id,
                Message.folder == folder
            )
            
            if status:
                query = query.filter(Message.status == status)
            
            # Sortuj - najnowsze najpierw
            query = query.order_by(Message.created_at.desc())
            
            return query.offset(offset).limit(limit).all()
        finally:
            db.close()
    
    def get_message(self, message_id: str) -> Optional[Message]:
        """Pobierz szczegóły wiadomości"""
        db = self._get_db()
        try:
            return db.query(Message).filter(Message.id == message_id).first()
        finally:
            db.close()
    
    def mark_as_read(self, message_id: str) -> Message:
        """Oznacz wiadomość jako przeczytaną"""
        db = self._get_db()
        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if message:
                message.status = "READ"
                message.read_at = datetime.utcnow()
                db.commit()
                db.refresh(message)
            return message
        finally:
            db.close()
    
    def archive_message(self, message_id: str) -> Message:
        """Przenieś wiadomość do archiwum"""
        db = self._get_db()
        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if message:
                message.folder = "archive"
                message.archived_at = datetime.utcnow()
                db.commit()
                db.refresh(message)
            return message
        finally:
            db.close()
    
    def delete_message(self, message_id: str, permanent: bool = False) -> bool:
        """Usuń wiadomość (do kosza lub permanentnie)"""
        db = self._get_db()
        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if message:
                if permanent:
                    db.delete(message)
                else:
                    message.folder = "trash"
                    message.deleted_at = datetime.utcnow()
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def move_message(self, message_id: str, to_folder: str) -> Message:
        """Przenieś wiadomość do innego folderu"""
        db = self._get_db()
        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if message:
                message.folder = to_folder
                db.commit()
                db.refresh(message)
            return message
        finally:
            db.close()
    
    def get_folder_stats(self, user_id: str) -> Dict[str, Dict[str, int]]:
        """Pobierz statystyki folderów"""
        db = self._get_db()
        try:
            stats = {}
            folders = ["inbox", "sent", "drafts", "trash", "archive"]
            
            for folder in folders:
                total = db.query(Message).filter(
                    Message.user_id == user_id,
                    Message.folder == folder
                ).count()
                
                unread = db.query(Message).filter(
                    Message.user_id == user_id,
                    Message.folder == folder,
                    Message.status.in_(["RECEIVED", "DRAFT"])
                ).count()
                
                stats[folder] = {"total": total, "unread": unread}
            
            return stats
        finally:
            db.close()
    
    def search_messages(
        self,
        user_id: str,
        query: str,
        folder: str = None,
        limit: int = 50
    ) -> List[Message]:
        """Wyszukaj wiadomości"""
        db = self._get_db()
        try:
            q = db.query(Message).filter(Message.user_id == user_id)
            
            if folder:
                q = q.filter(Message.folder == folder)
            
            # Wyszukiwanie w temacie i treści
            search_term = f"%{query}%"
            q = q.filter(
                (Message.subject.ilike(search_term)) |
                (Message.content.ilike(search_term))
            )
            
            return q.order_by(Message.created_at.desc()).limit(limit).all()
        finally:
            db.close()
    
    def to_response_dict(self, message: Message) -> Dict[str, Any]:
        """Konwertuj Message na słownik odpowiedzi API"""
        return {
            "id": message.id,
            "subject": message.subject,
            "content": message.content,
            "status": message.status,
            "folder": message.folder,
            "sender": {
                "address": message.sender_address,
                "name": message.sender_name
            } if message.sender_address else None,
            "recipient": {
                "address": message.recipient_address,
                "name": message.recipient_name
            } if message.recipient_address else None,
            "receivedAt": message.received_at.isoformat() if message.received_at else None,
            "sentAt": message.sent_at.isoformat() if message.sent_at else None,
            "createdAt": message.created_at.isoformat() if message.created_at else None,
            "attachments": message.attachments or []
        }


# Singleton instance
message_service = MessageService()
