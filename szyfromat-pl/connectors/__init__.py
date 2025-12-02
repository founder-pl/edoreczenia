"""
Szyfromat.pl Connectors
Moduły integracji z zewnętrznymi usługami
"""

from .ade.connector import ADEConnector
from .imap.connector import IMAPConnector, SMTPConnector
from .nextcloud.connector import NextcloudConnector

__all__ = [
    "ADEConnector",
    "IMAPConnector", 
    "SMTPConnector",
    "NextcloudConnector"
]
