"""
CQRS - Commands (Write Side)
Komendy reprezentują intencje użytkownika do zmiany stanu systemu.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class Command(BaseModel):
    """Base Command class"""
    command_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None

    class Config:
        use_enum_values = True


# ═══════════════════════════════════════════════════════════════
# MESSAGE COMMANDS
# ═══════════════════════════════════════════════════════════════

class CreateMessageCommand(Command):
    """Utwórz nową wiadomość (szkic)"""
    recipient: str
    subject: str
    content: str
    attachments: List[str] = []


class SendMessageCommand(Command):
    """Wyślij wiadomość"""
    message_id: str


class ReadMessageCommand(Command):
    """Oznacz wiadomość jako przeczytaną"""
    message_id: str


class ArchiveMessageCommand(Command):
    """Zarchiwizuj wiadomość"""
    message_id: str


class DeleteMessageCommand(Command):
    """Usuń wiadomość"""
    message_id: str
    permanent: bool = False


class MoveMessageCommand(Command):
    """Przenieś wiadomość do folderu"""
    message_id: str
    to_folder: str


class RestoreMessageCommand(Command):
    """Przywróć wiadomość z kosza"""
    message_id: str


# ═══════════════════════════════════════════════════════════════
# USER COMMANDS
# ═══════════════════════════════════════════════════════════════

class LoginCommand(Command):
    """Zaloguj użytkownika"""
    username: str
    password: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class LogoutCommand(Command):
    """Wyloguj użytkownika"""
    pass


class UpdateUserSettingsCommand(Command):
    """Zaktualizuj ustawienia użytkownika"""
    settings: dict


# ═══════════════════════════════════════════════════════════════
# FOLDER COMMANDS
# ═══════════════════════════════════════════════════════════════

class CreateFolderCommand(Command):
    """Utwórz nowy folder"""
    name: str
    parent_id: Optional[str] = None


class RenameFolderCommand(Command):
    """Zmień nazwę folderu"""
    folder_id: str
    new_name: str


class DeleteFolderCommand(Command):
    """Usuń folder"""
    folder_id: str


# ═══════════════════════════════════════════════════════════════
# SYNC COMMANDS
# ═══════════════════════════════════════════════════════════════

class StartSyncCommand(Command):
    """Rozpocznij synchronizację"""
    source: str  # "proxy", "sync", "dsl"


class StopSyncCommand(Command):
    """Zatrzymaj synchronizację"""
    sync_id: str
