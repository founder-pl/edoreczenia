"""
CQRS - Queries (Read Side)
Zapytania do odczytu danych z projekcji.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class Query(BaseModel):
    """Base Query class"""
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# MESSAGE QUERIES
# ═══════════════════════════════════════════════════════════════

class GetMessagesQuery(Query):
    """Pobierz listę wiadomości"""
    folder: str = "inbox"
    limit: int = 50
    offset: int = 0
    status: Optional[str] = None
    search: Optional[str] = None


class GetMessageQuery(Query):
    """Pobierz szczegóły wiadomości"""
    message_id: str


class GetMessageHistoryQuery(Query):
    """Pobierz historię zdarzeń wiadomości"""
    message_id: str


class SearchMessagesQuery(Query):
    """Wyszukaj wiadomości"""
    query: str
    folder: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = 50


# ═══════════════════════════════════════════════════════════════
# FOLDER QUERIES
# ═══════════════════════════════════════════════════════════════

class GetFoldersQuery(Query):
    """Pobierz listę folderów z licznikami"""
    pass


class GetFolderStatsQuery(Query):
    """Pobierz statystyki folderu"""
    folder_id: str


# ═══════════════════════════════════════════════════════════════
# USER QUERIES
# ═══════════════════════════════════════════════════════════════

class GetUserQuery(Query):
    """Pobierz dane użytkownika"""
    pass  # user_id z Query base


class GetUserActivityQuery(Query):
    """Pobierz aktywność użytkownika"""
    from_date: Optional[datetime] = None
    limit: int = 100


# ═══════════════════════════════════════════════════════════════
# ANALYTICS QUERIES
# ═══════════════════════════════════════════════════════════════

class GetDashboardStatsQuery(Query):
    """Pobierz statystyki dashboardu"""
    pass


class GetEventLogQuery(Query):
    """Pobierz log zdarzeń"""
    aggregate_id: Optional[str] = None
    event_type: Optional[str] = None
    from_date: Optional[datetime] = None
    limit: int = 100
