"""
e-Doręczenia Middleware Sync

Middleware synchronizujący e-Doręczenia z lokalną skrzynką IMAP.
Cyklicznie pobiera wiadomości z e-Doręczeń i importuje je do IMAP,
oraz wysyła wiadomości z IMAP do e-Doręczeń.
"""
from .api_client import EDoreczeniaClient, EDoreczeniaMessage
from .config import Settings, SyncDirection, get_settings
from .imap_client import IMAPMailbox
from .main import Application, main
from .models import Database, SyncRun, SyncStatus, SyncedMessage
from .sync_engine import SyncEngine

__version__ = "0.1.0"
__all__ = [
    "Application",
    "Database",
    "EDoreczeniaClient",
    "EDoreczeniaMessage",
    "IMAPMailbox",
    "Settings",
    "SyncDirection",
    "SyncEngine",
    "SyncRun",
    "SyncStatus",
    "SyncedMessage",
    "get_settings",
    "main",
]
