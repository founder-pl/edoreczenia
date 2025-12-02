"""
e-Doręczenia Proxy IMAP/SMTP

Most między protokołami pocztowymi IMAP/SMTP a REST API e-Doręczeń.
Umożliwia korzystanie z e-Doręczeń przez standardowe klienty poczty.
"""
from .api_client import EDoreczeniaClient, Message
from .config import Settings, get_settings
from .imap_server import IMAPServer, IMAPSession
from .main import Application, main
from .smtp_server import SMTPServer

__version__ = "0.1.0"
__all__ = [
    "Application",
    "EDoreczeniaClient",
    "IMAPServer",
    "IMAPSession",
    "Message",
    "Settings",
    "SMTPServer",
    "get_settings",
    "main",
]
