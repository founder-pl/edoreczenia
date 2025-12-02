"""
CQRS - Projections (Read Models)
Projekcje budują widoki danych na podstawie zdarzeń.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

from .events import Event, EventType
from .event_store import event_store


class MessageProjection:
    """
    Projekcja wiadomości - buduje aktualny stan wiadomości z zdarzeń.
    """
    
    def __init__(self):
        # Read models (in-memory, w produkcji: Redis, PostgreSQL read replica)
        self._messages: Dict[str, Dict[str, Any]] = {}
        self._messages_by_folder: Dict[str, List[str]] = defaultdict(list)
        self._messages_by_user: Dict[str, List[str]] = defaultdict(list)
        
        # Subskrybuj zdarzenia
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Zarejestruj handlery zdarzeń"""
        event_store.subscribe(EventType.MESSAGE_CREATED, self._on_message_created)
        event_store.subscribe(EventType.MESSAGE_SENT, self._on_message_sent)
        event_store.subscribe(EventType.MESSAGE_RECEIVED, self._on_message_received)
        event_store.subscribe(EventType.MESSAGE_READ, self._on_message_read)
        event_store.subscribe(EventType.MESSAGE_ARCHIVED, self._on_message_archived)
        event_store.subscribe(EventType.MESSAGE_DELETED, self._on_message_deleted)
        event_store.subscribe(EventType.MESSAGE_MOVED, self._on_message_moved)
    
    def _on_message_created(self, event: Event):
        """Handle MESSAGE_CREATED"""
        message_id = event.aggregate_id
        recipient = event.payload.get("recipient")
        if isinstance(recipient, str):
            recipient = {"address": recipient}
        
        self._messages[message_id] = {
            "id": message_id,
            "subject": event.payload.get("subject"),
            "recipient": recipient,
            "content": event.payload.get("content"),
            "status": "DRAFT",
            "folder": "drafts",
            "created_at": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "sender": {"address": event.user_id or "unknown", "name": "Użytkownik"},
            "version": event.version
        }
        self._messages_by_folder["drafts"].append(message_id)
        if event.user_id:
            self._messages_by_user[event.user_id].append(message_id)
    
    def _on_message_sent(self, event: Event):
        """Handle MESSAGE_SENT"""
        message_id = event.aggregate_id
        if message_id in self._messages:
            msg = self._messages[message_id]
            
            # Usuń z drafts
            if message_id in self._messages_by_folder["drafts"]:
                self._messages_by_folder["drafts"].remove(message_id)
            
            # Dodaj do sent
            self._messages_by_folder["sent"].append(message_id)
            
            # Aktualizuj stan
            msg["status"] = "SENT"
            msg["folder"] = "sent"
            msg["sent_at"] = event.payload.get("sent_at")
            msg["version"] = event.version
    
    def _on_message_received(self, event: Event):
        """Handle MESSAGE_RECEIVED"""
        message_id = event.aggregate_id
        self._messages[message_id] = {
            "id": message_id,
            "subject": event.payload.get("subject"),
            "sender": event.payload.get("sender"),
            "status": "RECEIVED",
            "folder": "inbox",
            "received_at": event.payload.get("received_at"),
            "version": event.version
        }
        self._messages_by_folder["inbox"].append(message_id)
    
    def _on_message_read(self, event: Event):
        """Handle MESSAGE_READ"""
        message_id = event.aggregate_id
        if message_id in self._messages:
            self._messages[message_id]["status"] = "READ"
            self._messages[message_id]["read_at"] = event.payload.get("read_at")
            self._messages[message_id]["version"] = event.version
    
    def _on_message_archived(self, event: Event):
        """Handle MESSAGE_ARCHIVED"""
        message_id = event.aggregate_id
        if message_id in self._messages:
            msg = self._messages[message_id]
            old_folder = msg.get("folder", "inbox")
            
            # Przenieś między folderami
            if message_id in self._messages_by_folder[old_folder]:
                self._messages_by_folder[old_folder].remove(message_id)
            self._messages_by_folder["archive"].append(message_id)
            
            msg["folder"] = "archive"
            msg["archived_at"] = event.payload.get("archived_at")
            msg["version"] = event.version
    
    def _on_message_deleted(self, event: Event):
        """Handle MESSAGE_DELETED"""
        message_id = event.aggregate_id
        if message_id in self._messages:
            msg = self._messages[message_id]
            old_folder = msg.get("folder", "inbox")
            
            if event.payload.get("permanent"):
                # Permanentne usunięcie
                if message_id in self._messages_by_folder[old_folder]:
                    self._messages_by_folder[old_folder].remove(message_id)
                del self._messages[message_id]
            else:
                # Przenieś do kosza
                if message_id in self._messages_by_folder[old_folder]:
                    self._messages_by_folder[old_folder].remove(message_id)
                self._messages_by_folder["trash"].append(message_id)
                
                msg["folder"] = "trash"
                msg["deleted_at"] = event.payload.get("deleted_at")
                msg["version"] = event.version
    
    def _on_message_moved(self, event: Event):
        """Handle MESSAGE_MOVED"""
        message_id = event.aggregate_id
        if message_id in self._messages:
            msg = self._messages[message_id]
            from_folder = event.payload.get("from_folder")
            to_folder = event.payload.get("to_folder")
            
            if message_id in self._messages_by_folder[from_folder]:
                self._messages_by_folder[from_folder].remove(message_id)
            self._messages_by_folder[to_folder].append(message_id)
            
            msg["folder"] = to_folder
            msg["version"] = event.version
    
    # ═══════════════════════════════════════════════════════════════
    # QUERY METHODS
    # ═══════════════════════════════════════════════════════════════
    
    def get_messages(self, folder: str = "inbox", limit: int = 50, offset: int = 0) -> List[Dict]:
        """Pobierz wiadomości z folderu"""
        message_ids = self._messages_by_folder.get(folder, [])
        result = []
        for msg_id in message_ids[offset:offset + limit]:
            if msg_id in self._messages:
                result.append(self._messages[msg_id])
        return result
    
    def get_message(self, message_id: str) -> Optional[Dict]:
        """Pobierz szczegóły wiadomości"""
        return self._messages.get(message_id)
    
    def get_folder_stats(self) -> Dict[str, Dict[str, int]]:
        """Pobierz statystyki folderów"""
        stats = {}
        for folder, message_ids in self._messages_by_folder.items():
            unread = sum(1 for mid in message_ids 
                        if mid in self._messages 
                        and self._messages[mid].get("status") in ["RECEIVED", "DRAFT"])
            stats[folder] = {
                "total": len(message_ids),
                "unread": unread
            }
        return stats
    
    def search(self, query: str, folder: Optional[str] = None) -> List[Dict]:
        """Wyszukaj wiadomości"""
        results = []
        query_lower = query.lower()
        
        messages = self._messages.values()
        if folder:
            message_ids = self._messages_by_folder.get(folder, [])
            messages = [self._messages[mid] for mid in message_ids if mid in self._messages]
        
        for msg in messages:
            if (query_lower in msg.get("subject", "").lower() or
                query_lower in msg.get("content", "").lower()):
                results.append(msg)
        
        return results


class FolderProjection:
    """Projekcja folderów"""
    
    def __init__(self, message_projection: MessageProjection):
        self.message_projection = message_projection
    
    def get_folders(self) -> List[Dict]:
        """Pobierz listę folderów z licznikami"""
        stats = self.message_projection.get_folder_stats()
        
        folders = [
            {"id": "inbox", "name": "Odebrane", "label": "INBOX"},
            {"id": "sent", "name": "Wysłane", "label": "SENT"},
            {"id": "drafts", "name": "Robocze", "label": "DRAFTS"},
            {"id": "trash", "name": "Kosz", "label": "TRASH"},
            {"id": "archive", "name": "Archiwum", "label": "ARCHIVE"},
        ]
        
        for folder in folders:
            folder_stats = stats.get(folder["id"], {"total": 0, "unread": 0})
            folder["total_count"] = folder_stats["total"]
            folder["unread_count"] = folder_stats["unread"]
        
        return folders


class UserActivityProjection:
    """Projekcja aktywności użytkownika"""
    
    def __init__(self):
        self._activities: Dict[str, List[Dict]] = defaultdict(list)
        self._setup_handlers()
    
    def _setup_handlers(self):
        event_store.subscribe_all(self._on_any_event)
    
    def _on_any_event(self, event: Event):
        if event.user_id:
            self._activities[event.user_id].append({
                "event_type": event.event_type,
                "aggregate_id": event.aggregate_id,
                "timestamp": event.timestamp.isoformat(),
                "payload": event.payload
            })
    
    def get_user_activity(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Pobierz aktywność użytkownika"""
        activities = self._activities.get(user_id, [])
        return activities[-limit:]


# ═══════════════════════════════════════════════════════════════
# SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════

message_projection = MessageProjection()
folder_projection = FolderProjection(message_projection)
user_activity_projection = UserActivityProjection()
