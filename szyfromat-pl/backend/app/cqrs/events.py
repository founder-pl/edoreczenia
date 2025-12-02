"""
Event Sourcing - Event Definitions
Wszystkie zdarzenia domenowe dla e-Doręczeń
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


class EventType(str, Enum):
    # Message Events
    MESSAGE_CREATED = "message.created"
    MESSAGE_SENT = "message.sent"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_READ = "message.read"
    MESSAGE_ARCHIVED = "message.archived"
    MESSAGE_DELETED = "message.deleted"
    MESSAGE_MOVED = "message.moved"
    MESSAGE_RESTORED = "message.restored"
    
    # Attachment Events
    ATTACHMENT_ADDED = "attachment.added"
    ATTACHMENT_DOWNLOADED = "attachment.downloaded"
    ATTACHMENT_REMOVED = "attachment.removed"
    
    # User Events
    USER_LOGGED_IN = "user.logged_in"
    USER_LOGGED_OUT = "user.logged_out"
    USER_SETTINGS_UPDATED = "user.settings_updated"
    
    # Folder Events
    FOLDER_CREATED = "folder.created"
    FOLDER_RENAMED = "folder.renamed"
    FOLDER_DELETED = "folder.deleted"
    
    # Integration Events
    SYNC_STARTED = "sync.started"
    SYNC_COMPLETED = "sync.completed"
    SYNC_FAILED = "sync.failed"
    
    # EPO Events (Electronic Proof of Delivery)
    EPO_REQUESTED = "epo.requested"
    EPO_CONFIRMED = "epo.confirmed"
    EPO_FAILED = "epo.failed"


class Event(BaseModel):
    """Base Event class for Event Sourcing"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    aggregate_id: str  # ID of the entity this event belongs to
    aggregate_type: str  # Type of entity (message, user, folder)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None  # For tracking related events
    causation_id: Optional[str] = None  # ID of event that caused this one
    metadata: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


# ═══════════════════════════════════════════════════════════════
# MESSAGE EVENTS
# ═══════════════════════════════════════════════════════════════

class MessageCreatedEvent(Event):
    """Wiadomość została utworzona (szkic)"""
    event_type: EventType = EventType.MESSAGE_CREATED
    aggregate_type: str = "message"
    
    def __init__(self, message_id: str, user_id: str, subject: str, recipient: str, content: str, **kwargs):
        super().__init__(
            aggregate_id=message_id,
            user_id=user_id,
            payload={
                "subject": subject,
                "recipient": recipient,
                "content": content,
                "status": "DRAFT"
            },
            **kwargs
        )


class MessageSentEvent(Event):
    """Wiadomość została wysłana"""
    event_type: EventType = EventType.MESSAGE_SENT
    aggregate_type: str = "message"
    
    def __init__(self, message_id: str, user_id: str, recipient: str, **kwargs):
        super().__init__(
            aggregate_id=message_id,
            user_id=user_id,
            payload={
                "recipient": recipient,
                "sent_at": datetime.utcnow().isoformat(),
                "status": "SENT"
            },
            **kwargs
        )


class MessageReceivedEvent(Event):
    """Wiadomość została odebrana"""
    event_type: EventType = EventType.MESSAGE_RECEIVED
    aggregate_type: str = "message"
    
    def __init__(self, message_id: str, sender: str, subject: str, **kwargs):
        super().__init__(
            aggregate_id=message_id,
            payload={
                "sender": sender,
                "subject": subject,
                "received_at": datetime.utcnow().isoformat(),
                "status": "RECEIVED"
            },
            **kwargs
        )


class MessageReadEvent(Event):
    """Wiadomość została przeczytana"""
    event_type: EventType = EventType.MESSAGE_READ
    aggregate_type: str = "message"
    
    def __init__(self, message_id: str, user_id: str, **kwargs):
        super().__init__(
            aggregate_id=message_id,
            user_id=user_id,
            payload={
                "read_at": datetime.utcnow().isoformat(),
                "status": "READ"
            },
            **kwargs
        )


class MessageArchivedEvent(Event):
    """Wiadomość została zarchiwizowana"""
    event_type: EventType = EventType.MESSAGE_ARCHIVED
    aggregate_type: str = "message"
    
    def __init__(self, message_id: str, user_id: str, **kwargs):
        super().__init__(
            aggregate_id=message_id,
            user_id=user_id,
            payload={
                "archived_at": datetime.utcnow().isoformat(),
                "folder": "archive"
            },
            **kwargs
        )


class MessageDeletedEvent(Event):
    """Wiadomość została usunięta"""
    event_type: EventType = EventType.MESSAGE_DELETED
    aggregate_type: str = "message"
    
    def __init__(self, message_id: str, user_id: str, permanent: bool = False, **kwargs):
        super().__init__(
            aggregate_id=message_id,
            user_id=user_id,
            payload={
                "deleted_at": datetime.utcnow().isoformat(),
                "permanent": permanent,
                "folder": "trash" if not permanent else None
            },
            **kwargs
        )


class MessageMovedEvent(Event):
    """Wiadomość została przeniesiona do innego folderu"""
    event_type: EventType = EventType.MESSAGE_MOVED
    aggregate_type: str = "message"
    
    def __init__(self, message_id: str, user_id: str, from_folder: str, to_folder: str, **kwargs):
        super().__init__(
            aggregate_id=message_id,
            user_id=user_id,
            payload={
                "from_folder": from_folder,
                "to_folder": to_folder,
                "moved_at": datetime.utcnow().isoformat()
            },
            **kwargs
        )


# ═══════════════════════════════════════════════════════════════
# USER EVENTS
# ═══════════════════════════════════════════════════════════════

class UserLoggedInEvent(Event):
    """Użytkownik zalogował się"""
    event_type: EventType = EventType.USER_LOGGED_IN
    aggregate_type: str = "user"
    
    def __init__(self, user_id: str, ip_address: str = None, user_agent: str = None, **kwargs):
        super().__init__(
            aggregate_id=user_id,
            user_id=user_id,
            payload={
                "logged_in_at": datetime.utcnow().isoformat(),
                "ip_address": ip_address,
                "user_agent": user_agent
            },
            **kwargs
        )


class UserLoggedOutEvent(Event):
    """Użytkownik wylogował się"""
    event_type: EventType = EventType.USER_LOGGED_OUT
    aggregate_type: str = "user"
    
    def __init__(self, user_id: str, **kwargs):
        super().__init__(
            aggregate_id=user_id,
            user_id=user_id,
            payload={
                "logged_out_at": datetime.utcnow().isoformat()
            },
            **kwargs
        )


# ═══════════════════════════════════════════════════════════════
# EPO EVENTS
# ═══════════════════════════════════════════════════════════════

class EPOConfirmedEvent(Event):
    """EPO (Electronic Proof of Delivery) potwierdzone"""
    event_type: EventType = EventType.EPO_CONFIRMED
    aggregate_type: str = "message"
    
    def __init__(self, message_id: str, epo_id: str, confirmed_at: datetime, **kwargs):
        super().__init__(
            aggregate_id=message_id,
            payload={
                "epo_id": epo_id,
                "confirmed_at": confirmed_at.isoformat(),
                "status": "EPO_CONFIRMED"
            },
            **kwargs
        )


# ═══════════════════════════════════════════════════════════════
# SYNC EVENTS
# ═══════════════════════════════════════════════════════════════

class SyncStartedEvent(Event):
    """Synchronizacja rozpoczęta"""
    event_type: EventType = EventType.SYNC_STARTED
    aggregate_type: str = "sync"
    
    def __init__(self, sync_id: str, user_id: str, source: str, **kwargs):
        super().__init__(
            aggregate_id=sync_id,
            user_id=user_id,
            payload={
                "source": source,
                "started_at": datetime.utcnow().isoformat()
            },
            **kwargs
        )


class SyncCompletedEvent(Event):
    """Synchronizacja zakończona"""
    event_type: EventType = EventType.SYNC_COMPLETED
    aggregate_type: str = "sync"
    
    def __init__(self, sync_id: str, user_id: str, messages_synced: int, **kwargs):
        super().__init__(
            aggregate_id=sync_id,
            user_id=user_id,
            payload={
                "messages_synced": messages_synced,
                "completed_at": datetime.utcnow().isoformat()
            },
            **kwargs
        )
