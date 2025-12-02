"""
Serwer SMTP proxy dla e-Doręczeń.
Przyjmuje wiadomości SMTP i przekazuje je do REST API e-Doręczeń.
"""
import asyncio
import email
from email import policy
from email.parser import BytesParser
from typing import Optional

import structlog
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP, AuthResult, Envelope, LoginPassword, Session

from .api_client import EDoreczeniaClient
from .config import Settings

logger = structlog.get_logger(__name__)


class EDoreczeniaAuthenticator:
    """Authenticator dla SMTP z lokalną autoryzacją."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.authenticated_sessions: set = set()

    async def __call__(
        self,
        server: SMTP,
        session: Session,
        envelope: Envelope,
        mechanism: str,
        auth_data: tuple,
    ) -> AuthResult:
        """Weryfikuje dane uwierzytelniające."""
        fail_nothandled = AuthResult(success=False, handled=False)

        if mechanism not in ("LOGIN", "PLAIN"):
            return fail_nothandled

        if not isinstance(auth_data, LoginPassword):
            return fail_nothandled

        username = auth_data.login.decode("utf-8")
        password = auth_data.password.decode("utf-8")

        if (
            username == self.settings.local_auth_username
            and password == self.settings.local_auth_password.get_secret_value()
        ):
            logger.info("SMTP: Użytkownik zalogowany", username=username)
            # Zapisz ID sesji jako uwierzytelnionej
            self.authenticated_sessions.add(id(session))
            session.auth_data = username  # Ustaw własny atrybut
            return AuthResult(success=True)
        else:
            logger.warning("SMTP: Nieudana próba logowania", username=username)
            return AuthResult(success=False, handled=True)
    
    def is_authenticated(self, session: Session) -> bool:
        """Sprawdza czy sesja jest uwierzytelniona."""
        return id(session) in self.authenticated_sessions or hasattr(session, 'auth_data')


class EDoreczeniaHandler:
    """Handler wiadomości SMTP przekazujący do e-Doręczeń."""

    def __init__(self, api_client: EDoreczeniaClient, settings: Settings, authenticator: EDoreczeniaAuthenticator = None):
        self.api_client = api_client
        self.settings = settings
        self.authenticator = authenticator

    async def handle_EHLO(
        self,
        server: SMTP,
        session: Session,
        envelope: Envelope,
        hostname: str,
        responses: list[str],
    ) -> list[str]:
        """Obsługuje EHLO z rozszerzeniami."""
        session.host_name = hostname
        return responses

    async def handle_MAIL(
        self,
        server: SMTP,
        session: Session,
        envelope: Envelope,
        address: str,
        mail_options: list[str],
    ) -> str:
        """Obsługuje MAIL FROM."""
        # Sprawdź autentykację - aiosmtpd ustawia login_data po AUTH
        # Loguj dla debugowania
        logger.debug(
            "SMTP MAIL FROM check",
            has_auth_data=hasattr(session, 'auth_data'),
            has_login_data=hasattr(session, 'login_data'),
            login_data=getattr(session, 'login_data', None),
            authenticated=getattr(session, 'authenticated', None),
        )
        
        # W aiosmtpd 1.4.x, po udanej autentykacji session.login_data jest ustawiane
        is_auth = bool(getattr(session, 'login_data', None))
        
        if not is_auth:
            return "530 5.7.0 Authentication required"

        envelope.mail_from = address
        envelope.mail_options.extend(mail_options)
        return "250 OK"

    async def handle_RCPT(
        self,
        server: SMTP,
        session: Session,
        envelope: Envelope,
        address: str,
        rcpt_options: list[str],
    ) -> str:
        """Obsługuje RCPT TO."""
        if not bool(getattr(session, 'login_data', None)):
            return "530 Authentication required"

        # Walidacja adresu e-Doręczeń (format AE:PL-...)
        if not self._validate_edoreczenia_address(address):
            logger.warning("SMTP: Nieprawidłowy adres e-Doręczeń", address=address)
            # Pozwalamy na email w formacie standardowym, który zostanie przetłumaczony
            pass

        envelope.rcpt_tos.append(address)
        envelope.rcpt_options.extend(rcpt_options)
        return "250 OK"

    async def handle_DATA(
        self,
        server: SMTP,
        session: Session,
        envelope: Envelope,
    ) -> str:
        """Obsługuje DATA - przetwarza i wysyła wiadomość."""
        if not bool(getattr(session, 'login_data', None)):
            return "530 Authentication required"

        try:
            # Parsowanie wiadomości MIME
            parser = BytesParser(policy=policy.default)
            msg = parser.parsebytes(envelope.content)

            subject = msg.get("Subject", "(brak tematu)")
            sender = envelope.mail_from
            recipients = envelope.rcpt_tos

            # Ekstrakcja treści
            content = self._extract_content(msg)

            # Ekstrakcja załączników
            attachments = self._extract_attachments(msg)

            # Translacja adresów na format e-Doręczeń
            edoreczenia_recipients = [
                self._translate_to_edoreczenia_address(r) for r in recipients
            ]

            logger.info(
                "SMTP: Wysyłanie wiadomości",
                subject=subject,
                sender=sender,
                recipients=edoreczenia_recipients,
                attachments_count=len(attachments),
            )

            # Wysłanie przez API e-Doręczeń
            result = await self.api_client.send_message(
                recipients=edoreczenia_recipients,
                subject=subject,
                content=content,
                attachments=attachments,
            )

            message_id = result.get("messageId", "unknown")
            logger.info("SMTP: Wiadomość wysłana", message_id=message_id)

            return f"250 OK: Message queued as {message_id}"

        except Exception as e:
            logger.error("SMTP: Błąd wysyłania", error=str(e))
            return f"451 Temporary error: {e}"

    def _extract_content(self, msg: email.message.Message) -> str:
        """Ekstrahuje treść tekstową z wiadomości."""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")

            # Fallback do text/html
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")

        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")

        return ""

    def _extract_attachments(self, msg: email.message.Message) -> list[dict]:
        """Ekstrahuje załączniki z wiadomości."""
        attachments = []

        if not msg.is_multipart():
            return attachments

        for part in msg.walk():
            content_disposition = part.get("Content-Disposition", "")

            if "attachment" in content_disposition:
                filename = part.get_filename() or "attachment"
                content_type = part.get_content_type()
                payload = part.get_payload(decode=True)

                if payload:
                    import base64

                    attachments.append({
                        "filename": filename,
                        "contentType": content_type,
                        "content": base64.b64encode(payload).decode("utf-8"),
                    })

                    logger.debug(
                        "SMTP: Znaleziono załącznik",
                        filename=filename,
                        content_type=content_type,
                        size=len(payload),
                    )

        return attachments

    def _validate_edoreczenia_address(self, address: str) -> bool:
        """Sprawdza czy adres jest w formacie e-Doręczeń."""
        # Format: AE:PL-XXXXX-XXXXX-XXXXX-XX
        import re

        pattern = r"^AE:PL-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{2}$"
        return bool(re.match(pattern, address))

    def _translate_to_edoreczenia_address(self, address: str) -> str:
        """
        Tłumaczy adres email na adres e-Doręczeń.

        Jeśli adres jest już w formacie e-Doręczeń, zwraca go bez zmian.
        W przeciwnym razie próbuje wyszukać mapowanie.
        """
        if self._validate_edoreczenia_address(address):
            return address

        # TODO: Implementacja wyszukiwania w rejestrze e-Doręczeń
        # Na razie zwracamy adres bez zmian
        logger.warning(
            "SMTP: Adres nie jest w formacie e-Doręczeń, przekazuję bez zmian",
            address=address,
        )
        return address


class SMTPServer:
    """Serwer SMTP proxy dla e-Doręczeń."""

    def __init__(self, settings: Settings, api_client: EDoreczeniaClient):
        self.settings = settings
        self.api_client = api_client
        self._controller: Optional[Controller] = None

    async def start(self) -> None:
        """Uruchamia serwer SMTP."""
        authenticator = EDoreczeniaAuthenticator(self.settings)
        handler = EDoreczeniaHandler(self.api_client, self.settings, authenticator)

        self._controller = Controller(
            handler,
            hostname=self.settings.smtp_host,
            port=self.settings.smtp_port,
            authenticator=authenticator,
            auth_required=False,  # Sprawdzamy ręcznie w handle_MAIL
            auth_require_tls=False,  # Dla testów lokalnych
        )

        self._controller.start()
        logger.info(
            "Serwer SMTP uruchomiony",
            host=self.settings.smtp_host,
            port=self.settings.smtp_port,
        )

    async def stop(self) -> None:
        """Zatrzymuje serwer SMTP."""
        if self._controller:
            self._controller.stop()
            logger.info("Serwer SMTP zatrzymany")

    def is_running(self) -> bool:
        """Sprawdza czy serwer działa."""
        return self._controller is not None and self._controller.server is not None
