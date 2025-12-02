"""
CQRS - Command Handlers
Obsługa komend i generowanie zdarzeń.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from .commands import (
    Command, CreateMessageCommand, SendMessageCommand, ReadMessageCommand,
    ArchiveMessageCommand, DeleteMessageCommand, MoveMessageCommand,
    LoginCommand, LogoutCommand, StartSyncCommand
)
from .events import (
    Event, MessageCreatedEvent, MessageSentEvent, MessageReadEvent,
    MessageArchivedEvent, MessageDeletedEvent, MessageMovedEvent,
    UserLoggedInEvent, UserLoggedOutEvent, SyncStartedEvent, SyncCompletedEvent
)
from .event_store import event_store


class CommandResult:
    """Wynik wykonania komendy"""
    def __init__(self, success: bool, data: Dict[str, Any] = None, error: str = None):
        self.success = success
        self.data = data or {}
        self.error = error


class CommandHandler:
    """Base Command Handler"""
    
    async def handle(self, command: Command) -> CommandResult:
        raise NotImplementedError


class MessageCommandHandler(CommandHandler):
    """Handler dla komend wiadomości"""
    
    async def handle_create(self, command: CreateMessageCommand) -> CommandResult:
        """Utwórz nową wiadomość"""
        message_id = f"msg-{uuid.uuid4().hex[:8]}"
        
        event = MessageCreatedEvent(
            message_id=message_id,
            user_id=command.user_id,
            subject=command.subject,
            recipient=command.recipient,
            content=command.content,
            correlation_id=command.correlation_id
        )
        
        await event_store.append(event)
        
        return CommandResult(
            success=True,
            data={
                "message_id": message_id,
                "status": "DRAFT",
                "event_id": event.event_id
            }
        )
    
    async def handle_send(self, command: SendMessageCommand) -> CommandResult:
        """Wyślij wiadomość"""
        # Pobierz historię wiadomości
        events = await event_store.get_aggregate_events(command.message_id)
        
        if not events:
            return CommandResult(success=False, error="Message not found")
        
        # Sprawdź czy wiadomość może być wysłana
        last_event = events[-1]
        if last_event.payload.get("status") == "SENT":
            return CommandResult(success=False, error="Message already sent")
        
        # Pobierz odbiorcę z pierwszego eventu
        create_event = events[0]
        recipient = create_event.payload.get("recipient", "unknown")
        
        event = MessageSentEvent(
            message_id=command.message_id,
            user_id=command.user_id,
            recipient=recipient,
            correlation_id=command.correlation_id,
            causation_id=last_event.event_id
        )
        
        await event_store.append(event)
        
        return CommandResult(
            success=True,
            data={
                "message_id": command.message_id,
                "status": "SENT",
                "sent_at": event.payload["sent_at"],
                "event_id": event.event_id
            }
        )
    
    async def handle_read(self, command: ReadMessageCommand) -> CommandResult:
        """Oznacz wiadomość jako przeczytaną"""
        event = MessageReadEvent(
            message_id=command.message_id,
            user_id=command.user_id,
            correlation_id=command.correlation_id
        )
        
        await event_store.append(event)
        
        return CommandResult(
            success=True,
            data={
                "message_id": command.message_id,
                "status": "READ",
                "event_id": event.event_id
            }
        )
    
    async def handle_archive(self, command: ArchiveMessageCommand) -> CommandResult:
        """Zarchiwizuj wiadomość"""
        event = MessageArchivedEvent(
            message_id=command.message_id,
            user_id=command.user_id,
            correlation_id=command.correlation_id
        )
        
        await event_store.append(event)
        
        return CommandResult(
            success=True,
            data={
                "message_id": command.message_id,
                "folder": "archive",
                "event_id": event.event_id
            }
        )
    
    async def handle_delete(self, command: DeleteMessageCommand) -> CommandResult:
        """Usuń wiadomość"""
        event = MessageDeletedEvent(
            message_id=command.message_id,
            user_id=command.user_id,
            permanent=command.permanent,
            correlation_id=command.correlation_id
        )
        
        await event_store.append(event)
        
        return CommandResult(
            success=True,
            data={
                "message_id": command.message_id,
                "permanent": command.permanent,
                "folder": "trash" if not command.permanent else None,
                "event_id": event.event_id
            }
        )
    
    async def handle_move(self, command: MoveMessageCommand) -> CommandResult:
        """Przenieś wiadomość"""
        # Pobierz aktualny folder z historii
        events = await event_store.get_aggregate_events(command.message_id)
        from_folder = "inbox"
        for e in reversed(events):
            if "folder" in e.payload:
                from_folder = e.payload["folder"]
                break
        
        event = MessageMovedEvent(
            message_id=command.message_id,
            user_id=command.user_id,
            from_folder=from_folder,
            to_folder=command.to_folder,
            correlation_id=command.correlation_id
        )
        
        await event_store.append(event)
        
        return CommandResult(
            success=True,
            data={
                "message_id": command.message_id,
                "from_folder": from_folder,
                "to_folder": command.to_folder,
                "event_id": event.event_id
            }
        )


class UserCommandHandler(CommandHandler):
    """Handler dla komend użytkownika"""
    
    async def handle_login(self, command: LoginCommand) -> CommandResult:
        """Zaloguj użytkownika"""
        # W produkcji: weryfikacja hasła
        user_id = f"user-{command.username}"
        
        event = UserLoggedInEvent(
            user_id=user_id,
            ip_address=command.ip_address,
            user_agent=command.user_agent,
            correlation_id=command.correlation_id
        )
        
        await event_store.append(event)
        
        return CommandResult(
            success=True,
            data={
                "user_id": user_id,
                "logged_in_at": event.payload["logged_in_at"],
                "event_id": event.event_id
            }
        )
    
    async def handle_logout(self, command: LogoutCommand) -> CommandResult:
        """Wyloguj użytkownika"""
        event = UserLoggedOutEvent(
            user_id=command.user_id,
            correlation_id=command.correlation_id
        )
        
        await event_store.append(event)
        
        return CommandResult(
            success=True,
            data={
                "user_id": command.user_id,
                "event_id": event.event_id
            }
        )


class SyncCommandHandler(CommandHandler):
    """Handler dla komend synchronizacji"""
    
    async def handle_start_sync(self, command: StartSyncCommand) -> CommandResult:
        """Rozpocznij synchronizację"""
        sync_id = f"sync-{uuid.uuid4().hex[:8]}"
        
        event = SyncStartedEvent(
            sync_id=sync_id,
            user_id=command.user_id,
            source=command.source,
            correlation_id=command.correlation_id
        )
        
        await event_store.append(event)
        
        return CommandResult(
            success=True,
            data={
                "sync_id": sync_id,
                "source": command.source,
                "started_at": event.payload["started_at"],
                "event_id": event.event_id
            }
        )


# ═══════════════════════════════════════════════════════════════
# COMMAND BUS
# ═══════════════════════════════════════════════════════════════

class CommandBus:
    """
    Command Bus - routuje komendy do odpowiednich handlerów.
    Implementuje wzorzec Mediator.
    """
    
    def __init__(self):
        self.message_handler = MessageCommandHandler()
        self.user_handler = UserCommandHandler()
        self.sync_handler = SyncCommandHandler()
    
    async def dispatch(self, command: Command) -> CommandResult:
        """Wyślij komendę do odpowiedniego handlera"""
        
        # Message commands
        if isinstance(command, CreateMessageCommand):
            return await self.message_handler.handle_create(command)
        elif isinstance(command, SendMessageCommand):
            return await self.message_handler.handle_send(command)
        elif isinstance(command, ReadMessageCommand):
            return await self.message_handler.handle_read(command)
        elif isinstance(command, ArchiveMessageCommand):
            return await self.message_handler.handle_archive(command)
        elif isinstance(command, DeleteMessageCommand):
            return await self.message_handler.handle_delete(command)
        elif isinstance(command, MoveMessageCommand):
            return await self.message_handler.handle_move(command)
        
        # User commands
        elif isinstance(command, LoginCommand):
            return await self.user_handler.handle_login(command)
        elif isinstance(command, LogoutCommand):
            return await self.user_handler.handle_logout(command)
        
        # Sync commands
        elif isinstance(command, StartSyncCommand):
            return await self.sync_handler.handle_start_sync(command)
        
        else:
            return CommandResult(success=False, error=f"Unknown command type: {type(command)}")


# Singleton instance
command_bus = CommandBus()
