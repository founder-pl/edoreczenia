"""
Główny moduł aplikacji e-Doręczenia Proxy IMAP/SMTP.
"""
import asyncio
import signal
import sys
from typing import Optional

import structlog

from .api_client import EDoreczeniaClient
from .config import Settings, get_settings
from .imap_server import IMAPServer
from .smtp_server import SMTPServer

logger = structlog.get_logger(__name__)


def configure_logging(settings: Settings) -> None:
    """Konfiguruje logowanie."""
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class Application:
    """Główna aplikacja proxy."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_client: Optional[EDoreczeniaClient] = None
        self.imap_server: Optional[IMAPServer] = None
        self.smtp_server: Optional[SMTPServer] = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Uruchamia aplikację."""
        logger.info("Uruchamianie e-Doręczenia Proxy IMAP/SMTP")

        # Inicjalizacja klienta API
        self.api_client = EDoreczeniaClient(self.settings)
        await self.api_client.__aenter__()

        # Uruchomienie serwerów
        self.imap_server = IMAPServer(self.settings, self.api_client)
        self.smtp_server = SMTPServer(self.settings, self.api_client)

        # Start SMTP (synchroniczny)
        await self.smtp_server.start()

        # Start IMAP (asynchroniczny)
        imap_task = asyncio.create_task(self.imap_server.start())

        logger.info(
            "Serwery uruchomione",
            imap_port=self.settings.imap_port,
            smtp_port=self.settings.smtp_port,
        )

        # Oczekiwanie na sygnał zamknięcia
        await self._shutdown_event.wait()

        # Zatrzymanie
        imap_task.cancel()
        try:
            await imap_task
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        """Zatrzymuje aplikację."""
        logger.info("Zatrzymywanie aplikacji...")

        if self.smtp_server:
            await self.smtp_server.stop()

        if self.imap_server:
            await self.imap_server.stop()

        if self.api_client:
            await self.api_client.__aexit__(None, None, None)

        logger.info("Aplikacja zatrzymana")

    def request_shutdown(self) -> None:
        """Żąda zamknięcia aplikacji."""
        self._shutdown_event.set()


async def run_app() -> None:
    """Uruchamia aplikację z obsługą sygnałów."""
    settings = get_settings()
    configure_logging(settings)

    app = Application(settings)

    # Rejestracja obsługi sygnałów
    loop = asyncio.get_event_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, app.request_shutdown)

    try:
        await app.start()
    finally:
        await app.stop()


def main() -> None:
    """Punkt wejścia aplikacji."""
    try:
        asyncio.run(run_app())
    except KeyboardInterrupt:
        logger.info("Przerwano przez użytkownika")
        sys.exit(0)
    except Exception as e:
        logger.error("Błąd krytyczny", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
