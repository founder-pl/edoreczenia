"""
Klient IMAP do synchronizacji z lokalną skrzynką pocztową.
"""
import email
import ssl
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

import structlog
from imapclient import IMAPClient

from .api_client import EDoreczeniaMessage
from .config import Settings

logger = structlog.get_logger(__name__)


class IMAPMailbox:
    """Klient IMAP do operacji na skrzynce pocztowej."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: Optional[IMAPClient] = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self) -> None:
        """Łączy się z serwerem IMAP."""
        logger.info(
            "Łączenie z serwerem IMAP",
            host=self.settings.target_imap_host,
            port=self.settings.target_imap_port,
        )

        ssl_context = ssl.create_default_context() if self.settings.target_imap_ssl else None

        self._client = IMAPClient(
            self.settings.target_imap_host,
            port=self.settings.target_imap_port,
            ssl=self.settings.target_imap_ssl,
            ssl_context=ssl_context,
        )

        self._client.login(
            self.settings.target_imap_username,
            self.settings.target_imap_password.get_secret_value(),
        )

        logger.info("Połączono z serwerem IMAP")

    def disconnect(self) -> None:
        """Rozłącza się z serwerem IMAP."""
        if self._client:
            try:
                self._client.logout()
            except Exception:
                pass
            self._client = None
            logger.info("Rozłączono z serwerem IMAP")

    def ensure_folder(self, folder: str) -> None:
        """Upewnia się, że folder istnieje (tworzy jeśli nie)."""
        try:
            self._client.select_folder(folder)
        except Exception:
            # Folder nie istnieje, utwórz go
            logger.info("Tworzenie folderu IMAP", folder=folder)

            # Utwórz hierarchię folderów
            parts = folder.split("/")
            current = ""

            for part in parts:
                current = f"{current}/{part}" if current else part
                try:
                    self._client.create_folder(current)
                    logger.debug("Folder utworzony", folder=current)
                except Exception:
                    # Folder może już istnieć
                    pass

            self._client.select_folder(folder)

    def append_message(
        self,
        folder: str,
        msg: EDoreczeniaMessage,
        attachments_data: Optional[list[tuple[bytes, str, str]]] = None,
    ) -> int:
        """
        Dodaje wiadomość do folderu IMAP.

        Args:
            folder: Nazwa folderu
            msg: Wiadomość z e-Doręczeń
            attachments_data: Lista (content, filename, content_type)

        Returns:
            UID dodanej wiadomości
        """
        self.ensure_folder(folder)

        # Tworzenie wiadomości MIME
        if attachments_data:
            mime_msg = MIMEMultipart()
            mime_msg.attach(MIMEText(msg.content, "plain", "utf-8"))

            if msg.content_html:
                mime_msg.attach(MIMEText(msg.content_html, "html", "utf-8"))

            # Załączniki
            for content, filename, content_type in attachments_data:
                attachment = MIMEApplication(content)
                attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=filename,
                )
                mime_msg.attach(attachment)
        else:
            if msg.content_html:
                mime_msg = MIMEMultipart("alternative")
                mime_msg.attach(MIMEText(msg.content, "plain", "utf-8"))
                mime_msg.attach(MIMEText(msg.content_html, "html", "utf-8"))
            else:
                mime_msg = MIMEText(msg.content, "plain", "utf-8")

        # Nagłówki
        mime_msg["From"] = msg.sender
        mime_msg["To"] = ", ".join(msg.recipients)
        mime_msg["Subject"] = msg.subject
        mime_msg["Date"] = msg.received_at.strftime("%a, %d %b %Y %H:%M:%S +0000")
        mime_msg["Message-ID"] = f"<{msg.message_id}@edoreczenia.gov.pl>"
        mime_msg["X-EDoreczenia-ID"] = msg.message_id
        mime_msg["X-EDoreczenia-Status"] = msg.status

        # Dodaj flagę EPO jeśli istnieje
        if msg.epo:
            mime_msg["X-EDoreczenia-EPO"] = "true"

        # Dodanie do IMAP
        flags = []
        if msg.is_read:
            flags.append("\\Seen")

        raw_message = mime_msg.as_bytes()

        result = self._client.append(
            folder,
            raw_message,
            flags=flags,
            msg_time=msg.received_at,
        )

        # Wyciągnij UID z odpowiedzi
        # imapclient.append() zwraca bytes z odpowiedzią serwera lub None
        uid = None
        if result:
            # Odpowiedź może zawierać APPENDUID w formacie: b'[APPENDUID 123 456]'
            if isinstance(result, bytes):
                result_str = result.decode("utf-8", errors="replace")
                if "APPENDUID" in result_str:
                    # Parsuj APPENDUID z odpowiedzi
                    import re
                    match = re.search(r"APPENDUID\s+\d+\s+(\d+)", result_str)
                    if match:
                        uid = int(match.group(1))
            elif isinstance(result, dict):
                uid = result.get("APPENDUID", (None, None))[1]

        logger.info(
            "Wiadomość dodana do IMAP",
            folder=folder,
            uid=uid,
            message_id=msg.message_id,
        )

        return uid

    def get_outgoing_messages(self, folder: str) -> list[dict[str, Any]]:
        """
        Pobiera wiadomości do wysłania z folderu.

        Zwraca listę słowników z danymi wiadomości.
        """
        try:
            self._client.select_folder(folder)
        except Exception:
            logger.debug("Folder wychodzący nie istnieje", folder=folder)
            return []

        # Szukaj wiadomości bez flagi \Answered (niewysłane)
        uids = self._client.search(["NOT", "ANSWERED"])

        if not uids:
            return []

        messages = []
        fetch_data = self._client.fetch(uids, ["RFC822", "FLAGS", "INTERNALDATE"])

        for uid, data in fetch_data.items():
            raw_message = data[b"RFC822"]
            flags = data[b"FLAGS"]
            internal_date = data[b"INTERNALDATE"]

            parsed = email.message_from_bytes(raw_message)

            # Ekstrakcja danych
            recipients = []
            for header in ["To", "Cc", "Bcc"]:
                if parsed[header]:
                    recipients.extend(
                        addr.strip()
                        for addr in parsed[header].split(",")
                        if addr.strip()
                    )

            # Ekstrakcja treści
            content = ""
            attachments = []

            if parsed.is_multipart():
                for part in parsed.walk():
                    content_type = part.get_content_type()
                    disposition = part.get("Content-Disposition", "")

                    if "attachment" in disposition:
                        attachments.append({
                            "filename": part.get_filename() or "attachment",
                            "content_type": content_type,
                            "content": part.get_payload(decode=True),
                        })
                    elif content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            content = payload.decode("utf-8", errors="replace")
            else:
                payload = parsed.get_payload(decode=True)
                if payload:
                    content = payload.decode("utf-8", errors="replace")

            messages.append({
                "uid": uid,
                "subject": parsed.get("Subject", "(brak tematu)"),
                "sender": parsed.get("From", ""),
                "recipients": recipients,
                "content": content,
                "attachments": attachments,
                "date": internal_date,
                "flags": flags,
                "raw": raw_message,
            })

        logger.info("Pobrano wiadomości do wysłania", count=len(messages), folder=folder)
        return messages

    def mark_as_sent(self, folder: str, uid: int) -> None:
        """Oznacza wiadomość jako wysłaną (dodaje flagę \\Answered)."""
        self._client.select_folder(folder)
        self._client.add_flags([uid], ["\\Answered"])
        logger.debug("Wiadomość oznaczona jako wysłana", uid=uid)

    def move_to_sent(self, uid: int, source_folder: str, sent_folder: str) -> None:
        """Przenosi wiadomość do folderu wysłanych."""
        self.ensure_folder(sent_folder)
        self._client.select_folder(source_folder)
        self._client.move([uid], sent_folder)
        logger.debug("Wiadomość przeniesiona do wysłanych", uid=uid, folder=sent_folder)

    def get_folder_stats(self, folder: str) -> dict[str, int]:
        """Zwraca statystyki folderu."""
        try:
            status = self._client.folder_status(folder, ["MESSAGES", "UNSEEN", "RECENT"])
            return {
                "total": status.get(b"MESSAGES", 0),
                "unseen": status.get(b"UNSEEN", 0),
                "recent": status.get(b"RECENT", 0),
            }
        except Exception:
            return {"total": 0, "unseen": 0, "recent": 0}

    def list_folders(self) -> list[str]:
        """Zwraca listę wszystkich folderów."""
        folders = self._client.list_folders()
        return [f[2] for f in folders]  # (flags, delimiter, name)

    def search_by_header(
        self,
        folder: str,
        header_name: str,
        header_value: str,
    ) -> list[int]:
        """Szuka wiadomości po nagłówku."""
        self._client.select_folder(folder)
        return self._client.search(["HEADER", header_name, header_value])

    def message_exists(self, folder: str, edoreczenia_id: str) -> bool:
        """Sprawdza czy wiadomość o danym ID e-Doręczeń już istnieje."""
        uids = self.search_by_header(folder, "X-EDoreczenia-ID", edoreczenia_id)
        return len(uids) > 0
