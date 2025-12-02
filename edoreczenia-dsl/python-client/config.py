"""
e-Doręczenia DSL - Konfiguracja

Ładuje zmienne z .env i udostępnia jako obiekt konfiguracji.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


def load_env(env_path: Optional[str] = None):
    """Ładuje zmienne z pliku .env"""
    if env_path is None:
        env_path = Path(__file__).parent.parent / '.env'
    
    if Path(env_path).exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value


# Załaduj .env przy imporcie
load_env()


@dataclass
class Config:
    """Konfiguracja DSL z .env"""
    
    # Porty Docker
    dsl_port: int = int(os.getenv('DSL_PORT', '8090'))
    simulator_port: int = int(os.getenv('SIMULATOR_PORT', '8180'))
    dovecot_port: int = int(os.getenv('DOVECOT_PORT', '21143'))
    proxy_imap_port: int = int(os.getenv('PROXY_IMAP_PORT', '11143'))
    proxy_smtp_port: int = int(os.getenv('PROXY_SMTP_PORT', '11025'))
    
    # API e-Doręczeń
    api_url: str = os.getenv('EDORECZENIA_API_URL', 'http://localhost:8180')
    api_internal_url: str = os.getenv('EDORECZENIA_API_INTERNAL_URL', 'http://edoreczenia-simulator:8080')
    address: str = os.getenv('EDORECZENIA_ADDRESS', 'AE:PL-12345-67890-ABCDE-12')
    
    # OAuth2
    client_id: str = os.getenv('EDORECZENIA_CLIENT_ID', 'test_client_id')
    client_secret: str = os.getenv('EDORECZENIA_CLIENT_SECRET', 'test_client_secret')
    
    # IMAP Dovecot
    dovecot_host: str = os.getenv('DOVECOT_HOST', 'localhost')
    dovecot_internal_host: str = os.getenv('DOVECOT_INTERNAL_HOST', 'dovecot')
    imap_user: str = os.getenv('IMAP_USER', 'mailuser')
    imap_password: str = os.getenv('IMAP_PASSWORD', 'mailpass123')
    
    # IMAP/SMTP Proxy
    proxy_host: str = os.getenv('PROXY_HOST', 'localhost')
    proxy_internal_host: str = os.getenv('PROXY_INTERNAL_HOST', 'edoreczenia-proxy')
    smtp_user: str = os.getenv('SMTP_USER', 'testuser')
    smtp_password: str = os.getenv('SMTP_PASSWORD', 'testpass123')
    
    # Funkcje
    auto_sync: bool = os.getenv('AUTO_SYNC', 'false').lower() == 'true'
    file_watch: bool = os.getenv('FILE_WATCH', 'false').lower() == 'true'
    
    # Domyślne
    default_recipient: str = os.getenv('DEFAULT_RECIPIENT', 'AE:PL-ODBIORCA-TEST-00001')
    default_sender_name: str = os.getenv('DEFAULT_SENDER_NAME', 'Nadawca Testowy')
    
    # Logowanie
    log_level: str = os.getenv('LOG_LEVEL', 'DEBUG')
    log_dir: str = os.getenv('LOG_DIR', './logs')
    log_format: str = os.getenv('LOG_FORMAT', 'markdown')


# Singleton konfiguracji
config = Config()
