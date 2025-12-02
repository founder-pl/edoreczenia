"""
Konfiguracja aplikacji proxy IMAP/SMTP dla e-Doręczeń.
"""
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ustawienia aplikacji proxy."""

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

    # Serwer IMAP
    imap_host: str = Field(default="0.0.0.0", description="Host serwera IMAP")
    imap_port: int = Field(default=1143, description="Port IMAP (bez SSL)")
    imap_ssl_port: int = Field(default=1993, description="Port IMAP (SSL)")
    imap_ssl_cert: Optional[Path] = Field(default=None, description="Ścieżka do certyfikatu SSL")
    imap_ssl_key: Optional[Path] = Field(default=None, description="Ścieżka do klucza SSL")

    # Serwer SMTP
    smtp_host: str = Field(default="0.0.0.0", description="Host serwera SMTP")
    smtp_port: int = Field(default=1025, description="Port SMTP (bez SSL)")
    smtp_ssl_port: int = Field(default=1465, description="Port SMTP (SSL)")
    smtp_ssl_cert: Optional[Path] = Field(default=None, description="Ścieżka do certyfikatu SSL")
    smtp_ssl_key: Optional[Path] = Field(default=None, description="Ścieżka do klucza SSL")

    # Autoryzacja lokalna
    local_auth_username: str = Field(default="edoreczenia", description="Nazwa użytkownika")
    local_auth_password: SecretStr = Field(..., description="Hasło użytkownika")

    # Logowanie
    log_level: str = Field(default="INFO", description="Poziom logowania")
    log_format: str = Field(default="json", description="Format logów (json/text)")

    # Cache
    cache_ttl_seconds: int = Field(default=300, description="TTL cache w sekundach")
    cache_max_size: int = Field(default=1000, description="Maksymalny rozmiar cache")

    # Debug
    debug: bool = Field(default=False, description="Tryb debug")


def get_settings() -> Settings:
    """Zwraca instancję ustawień."""
    return Settings()
