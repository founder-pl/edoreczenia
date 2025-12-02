"""
Konfiguracja middleware synchronizującego e-Doręczenia z IMAP.
"""
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SyncDirection(str, Enum):
    """Kierunek synchronizacji."""

    INCOMING = "incoming"  # Tylko pobieranie z e-Doręczeń
    OUTGOING = "outgoing"  # Tylko wysyłanie do e-Doręczeń
    BIDIRECTIONAL = "bidirectional"  # W obie strony


class Settings(BaseSettings):
    """Ustawienia middleware."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # OAuth2 / Autoryzacja e-Doręczeń
    edoreczenia_client_id: str = Field(..., description="Client ID dla OAuth2")
    edoreczenia_client_secret: SecretStr = Field(..., description="Client Secret dla OAuth2")
    edoreczenia_token_url: str = Field(
        default="https://edoreczenia-api.gov.pl/oauth/token",
        description="URL endpointu tokenu OAuth2",
    )
    edoreczenia_api_base_url: str = Field(
        default="https://edoreczenia-api.gov.pl/ua/v5",
        description="Bazowy URL API e-Doręczeń",
    )

    # Adres e-Doręczeń
    edoreczenia_address: str = Field(..., description="Adres e-Doręczeń (AE:PL-...)")

    # Docelowy serwer IMAP
    target_imap_host: str = Field(..., description="Host serwera IMAP")
    target_imap_port: int = Field(default=993, description="Port IMAP")
    target_imap_ssl: bool = Field(default=True, description="Czy używać SSL")
    target_imap_username: str = Field(..., description="Użytkownik IMAP")
    target_imap_password: SecretStr = Field(..., description="Hasło IMAP")

    # Docelowy serwer SMTP
    target_smtp_host: str = Field(..., description="Host serwera SMTP")
    target_smtp_port: int = Field(default=587, description="Port SMTP")
    target_smtp_ssl: bool = Field(default=True, description="Czy używać SSL/TLS")
    target_smtp_username: str = Field(..., description="Użytkownik SMTP")
    target_smtp_password: SecretStr = Field(..., description="Hasło SMTP")

    # Synchronizacja
    sync_interval_minutes: int = Field(default=5, description="Interwał synchronizacji")
    sync_batch_size: int = Field(default=50, description="Rozmiar batcha")
    sync_direction: SyncDirection = Field(
        default=SyncDirection.BIDIRECTIONAL,
        description="Kierunek synchronizacji",
    )

    # Folder mapowania
    folder_mapping_inbox: str = Field(
        default="INBOX/e-Doreczenia",
        description="Folder dla wiadomości przychodzących",
    )
    folder_mapping_sent: str = Field(
        default="Sent/e-Doreczenia",
        description="Folder dla wiadomości wysłanych",
    )
    folder_mapping_outbox: str = Field(
        default="Drafts/e-Doreczenia-Wyslij",
        description="Folder dla wiadomości do wysłania",
    )

    # Baza danych
    database_url: str = Field(
        default="sqlite:///./sync_state.db",
        description="URL bazy danych",
    )

    # Logowanie
    log_level: str = Field(default="INFO", description="Poziom logowania")
    log_format: str = Field(default="json", description="Format logów")
    log_file: Optional[Path] = Field(default=None, description="Plik logów")

    # Powiadomienia
    notify_email: Optional[str] = Field(default=None, description="Email do powiadomień")
    notify_on_error: bool = Field(default=True, description="Powiadomienia o błędach")
    notify_on_success: bool = Field(default=False, description="Powiadomienia o sukcesie")

    # Debug
    debug: bool = Field(default=False, description="Tryb debug")


def get_settings() -> Settings:
    """Zwraca instancję ustawień."""
    return Settings()
