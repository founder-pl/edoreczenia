"""
CQRS - Query Handlers
Obsługa zapytań i zwracanie danych z projekcji.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from .queries import (
    Query, GetMessagesQuery, GetMessageQuery, GetMessageHistoryQuery,
    GetFoldersQuery, GetUserActivityQuery, GetEventLogQuery, GetDashboardStatsQuery
)
from .projections import message_projection, folder_projection, user_activity_projection
from .event_store import event_store


class QueryResult:
    """Wynik zapytania"""
    def __init__(self, success: bool, data: Any = None, error: str = None):
        self.success = success
        self.data = data
        self.error = error


class MessageQueryHandler:
    """Handler dla zapytań o wiadomości"""
    
    async def handle_get_messages(self, query: GetMessagesQuery) -> QueryResult:
        """Pobierz listę wiadomości"""
        messages = message_projection.get_messages(
            folder=query.folder,
            limit=query.limit,
            offset=query.offset
        )
        return QueryResult(success=True, data=messages)
    
    async def handle_get_message(self, query: GetMessageQuery) -> QueryResult:
        """Pobierz szczegóły wiadomości"""
        message = message_projection.get_message(query.message_id)
        if message:
            return QueryResult(success=True, data=message)
        return QueryResult(success=False, error="Message not found")
    
    async def handle_get_message_history(self, query: GetMessageHistoryQuery) -> QueryResult:
        """Pobierz historię zdarzeń wiadomości"""
        events = await event_store.get_aggregate_events(query.message_id)
        history = [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "timestamp": e.timestamp.isoformat(),
                "version": e.version,
                "payload": e.payload
            }
            for e in events
        ]
        return QueryResult(success=True, data=history)


class FolderQueryHandler:
    """Handler dla zapytań o foldery"""
    
    async def handle_get_folders(self, query: GetFoldersQuery) -> QueryResult:
        """Pobierz listę folderów"""
        folders = folder_projection.get_folders()
        return QueryResult(success=True, data=folders)


class UserQueryHandler:
    """Handler dla zapytań o użytkownika"""
    
    async def handle_get_activity(self, query: GetUserActivityQuery) -> QueryResult:
        """Pobierz aktywność użytkownika"""
        activity = user_activity_projection.get_user_activity(
            user_id=query.user_id,
            limit=query.limit
        )
        return QueryResult(success=True, data=activity)


class AnalyticsQueryHandler:
    """Handler dla zapytań analitycznych"""
    
    async def handle_get_dashboard_stats(self, query: GetDashboardStatsQuery) -> QueryResult:
        """Pobierz statystyki dashboardu"""
        folder_stats = message_projection.get_folder_stats()
        event_stats = event_store.get_stats()
        
        return QueryResult(success=True, data={
            "folders": folder_stats,
            "events": event_stats,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def handle_get_event_log(self, query: GetEventLogQuery) -> QueryResult:
        """Pobierz log zdarzeń"""
        if query.aggregate_id:
            events = await event_store.get_aggregate_events(query.aggregate_id)
        elif query.from_date:
            events = await event_store.get_events_since(query.from_date, query.limit)
        else:
            events = await event_store.get_all_events(limit=query.limit)
        
        log = [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "aggregate_id": e.aggregate_id,
                "aggregate_type": e.aggregate_type,
                "timestamp": e.timestamp.isoformat(),
                "user_id": e.user_id,
                "payload": e.payload
            }
            for e in events
        ]
        
        return QueryResult(success=True, data=log)


# ═══════════════════════════════════════════════════════════════
# QUERY BUS
# ═══════════════════════════════════════════════════════════════

class QueryBus:
    """
    Query Bus - routuje zapytania do odpowiednich handlerów.
    """
    
    def __init__(self):
        self.message_handler = MessageQueryHandler()
        self.folder_handler = FolderQueryHandler()
        self.user_handler = UserQueryHandler()
        self.analytics_handler = AnalyticsQueryHandler()
    
    async def dispatch(self, query: Query) -> QueryResult:
        """Wyślij zapytanie do odpowiedniego handlera"""
        
        # Message queries
        if isinstance(query, GetMessagesQuery):
            return await self.message_handler.handle_get_messages(query)
        elif isinstance(query, GetMessageQuery):
            return await self.message_handler.handle_get_message(query)
        elif isinstance(query, GetMessageHistoryQuery):
            return await self.message_handler.handle_get_message_history(query)
        
        # Folder queries
        elif isinstance(query, GetFoldersQuery):
            return await self.folder_handler.handle_get_folders(query)
        
        # User queries
        elif isinstance(query, GetUserActivityQuery):
            return await self.user_handler.handle_get_activity(query)
        
        # Analytics queries
        elif isinstance(query, GetDashboardStatsQuery):
            return await self.analytics_handler.handle_get_dashboard_stats(query)
        elif isinstance(query, GetEventLogQuery):
            return await self.analytics_handler.handle_get_event_log(query)
        
        else:
            return QueryResult(success=False, error=f"Unknown query type: {type(query)}")


# Singleton instance
query_bus = QueryBus()
