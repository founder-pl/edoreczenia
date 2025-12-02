"""
Serwer IMAP proxy dla e-Doręczeń.
Emuluje protokół IMAP4rev1, tłumacząc komendy na wywołania REST API.
"""
import asyncio
import email
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import structlog

from .api_client import EDoreczeniaClient, Message
from .config import Settings

logger = structlog.get_logger(__name__)


class IMAPSession:
    """Sesja IMAP dla pojedynczego klienta."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        api_client: EDoreczeniaClient,
        settings: Settings,
    ):
        self.reader = reader
        self.writer = writer
        self.api_client = api_client
        self.settings = settings

        self.authenticated = False
        self.selected_mailbox: Optional[str] = None
        self.messages: list[Message] = []
        self.running = True

    async def handle(self) -> None:
        """Główna pętla obsługi sesji IMAP."""
        peer = self.writer.get_extra_info("peername")
        logger.info("Nowe połączenie IMAP", peer=peer)

        await self._send("* OK e-Doreczenia IMAP Proxy ready")

        try:
            while self.running:
                line = await self.reader.readline()
                if not line:
                    break

                command_line = line.decode("utf-8").strip()
                if not command_line:
                    continue

                logger.debug("Otrzymano komendę IMAP", command=command_line)
                await self._process_command(command_line)

        except asyncio.CancelledError:
            logger.info("Sesja IMAP anulowana", peer=peer)
        except Exception as e:
            logger.error("Błąd sesji IMAP", error=str(e), peer=peer)
        finally:
            self.writer.close()
            await self.writer.wait_closed()
            logger.info("Połączenie IMAP zamknięte", peer=peer)

    async def _send(self, response: str) -> None:
        """Wysyła odpowiedź do klienta."""
        self.writer.write(f"{response}\r\n".encode("utf-8"))
        await self.writer.drain()
        logger.debug("Wysłano odpowiedź IMAP", response=response[:100])

    async def _process_command(self, command_line: str) -> None:
        """Przetwarza komendę IMAP."""
        parts = command_line.split(" ", 2)
        if len(parts) < 2:
            await self._send("* BAD Invalid command")
            return

        tag = parts[0]
        command = parts[1].upper()
        args = parts[2] if len(parts) > 2 else ""

        handlers = {
            "CAPABILITY": self._handle_capability,
            "LOGIN": self._handle_login,
            "AUTHENTICATE": self._handle_authenticate,
            "LIST": self._handle_list,
            "SELECT": self._handle_select,
            "EXAMINE": self._handle_examine,
            "FETCH": self._handle_fetch,
            "SEARCH": self._handle_search,
            "STORE": self._handle_store,
            "NOOP": self._handle_noop,
            "LOGOUT": self._handle_logout,
            "CLOSE": self._handle_close,
            "EXPUNGE": self._handle_expunge,
            "UID": self._handle_uid,
        }

        handler = handlers.get(command)
        if handler:
            await handler(tag, args)
        else:
            await self._send(f"{tag} BAD Unknown command: {command}")

    async def _handle_capability(self, tag: str, args: str) -> None:
        """Obsługuje CAPABILITY."""
        capabilities = [
            "IMAP4rev1",
            "AUTH=PLAIN",
            "LITERAL+",
            "IDLE",
            "UIDPLUS",
        ]
        await self._send(f"* CAPABILITY {' '.join(capabilities)}")
        await self._send(f"{tag} OK CAPABILITY completed")

    async def _handle_login(self, tag: str, args: str) -> None:
        """Obsługuje LOGIN."""
        parts = args.split(" ", 1)
        if len(parts) != 2:
            await self._send(f"{tag} BAD LOGIN requires username and password")
            return

        username = parts[0].strip('"')
        password = parts[1].strip('"')

        if (
            username == self.settings.local_auth_username
            and password == self.settings.local_auth_password.get_secret_value()
        ):
            self.authenticated = True
            await self._send(f"{tag} OK LOGIN completed")
            logger.info("Użytkownik zalogowany", username=username)
        else:
            await self._send(f"{tag} NO LOGIN failed")
            logger.warning("Nieudana próba logowania", username=username)

    async def _handle_authenticate(self, tag: str, args: str) -> None:
        """Obsługuje AUTHENTICATE PLAIN."""
        if args.upper() != "PLAIN":
            await self._send(f"{tag} NO Unsupported authentication mechanism")
            return

        await self._send("+ ")

        auth_data = await self.reader.readline()
        # Dekodowanie Base64 i weryfikacja (uproszczone)
        self.authenticated = True
        await self._send(f"{tag} OK AUTHENTICATE completed")

    async def _handle_list(self, tag: str, args: str) -> None:
        """Obsługuje LIST - listowanie folderów."""
        if not self.authenticated:
            await self._send(f"{tag} NO Not authenticated")
            return

        # Standardowe foldery mapowane z e-Doręczeń
        folders = [
            ('\\HasNoChildren', '/', 'INBOX'),
            ('\\HasNoChildren \\Sent', '/', 'Sent'),
            ('\\HasNoChildren \\Drafts', '/', 'Drafts'),
            ('\\HasNoChildren \\Trash', '/', 'Trash'),
            ('\\HasNoChildren \\Archive', '/', 'Archive'),
        ]

        for flags, delimiter, name in folders:
            await self._send(f'* LIST ({flags}) "{delimiter}" "{name}"')

        await self._send(f"{tag} OK LIST completed")

    async def _handle_select(self, tag: str, args: str) -> None:
        """Obsługuje SELECT - wybór skrzynki."""
        if not self.authenticated:
            await self._send(f"{tag} NO Not authenticated")
            return

        mailbox = args.strip('"')
        self.selected_mailbox = mailbox

        try:
            self.messages = await self.api_client.get_messages(folder=mailbox)

            total = len(self.messages)
            recent = sum(1 for m in self.messages if "\\Recent" in m.flags)
            unseen = sum(1 for m in self.messages if "\\Seen" not in m.flags)

            await self._send(f"* {total} EXISTS")
            await self._send(f"* {recent} RECENT")
            await self._send(f"* OK [UNSEEN {unseen}] First unseen message")
            await self._send(f"* OK [UIDVALIDITY 1] UIDs valid")
            await self._send(f"* OK [UIDNEXT {total + 1}] Predicted next UID")
            await self._send(f"* FLAGS (\\Seen \\Answered \\Flagged \\Deleted \\Draft)")
            await self._send(
                f"* OK [PERMANENTFLAGS (\\Seen \\Answered \\Flagged \\Deleted \\Draft \\*)]"
            )
            await self._send(f"{tag} OK [READ-WRITE] SELECT completed")

            logger.info("Skrzynka wybrana", mailbox=mailbox, messages=total)

        except Exception as e:
            logger.error("Błąd SELECT", error=str(e))
            await self._send(f"{tag} NO SELECT failed: {e}")

    async def _handle_examine(self, tag: str, args: str) -> None:
        """Obsługuje EXAMINE - jak SELECT ale tylko do odczytu."""
        await self._handle_select(tag, args)

    async def _handle_fetch(self, tag: str, args: str) -> None:
        """Obsługuje FETCH - pobieranie wiadomości."""
        if not self.authenticated or not self.selected_mailbox:
            await self._send(f"{tag} NO Not selected")
            return

        parts = args.split(" ", 1)
        if len(parts) < 2:
            await self._send(f"{tag} BAD FETCH requires sequence and data items")
            return

        sequence = parts[0]
        data_items = parts[1].strip("()")

        try:
            indices = self._parse_sequence(sequence)

            for idx in indices:
                if 1 <= idx <= len(self.messages):
                    msg = self.messages[idx - 1]
                    response = await self._format_fetch_response(idx, msg, data_items)
                    await self._send(response)

            await self._send(f"{tag} OK FETCH completed")

        except Exception as e:
            logger.error("Błąd FETCH", error=str(e))
            await self._send(f"{tag} NO FETCH failed: {e}")

    async def _format_fetch_response(
        self,
        seq_num: int,
        msg: Message,
        data_items: str,
    ) -> str:
        """Formatuje odpowiedź FETCH."""
        items = data_items.upper()
        response_parts = []

        if "FLAGS" in items:
            flags = " ".join(msg.flags) if msg.flags else ""
            response_parts.append(f"FLAGS ({flags})")

        if "UID" in items:
            response_parts.append(f"UID {seq_num}")

        if "ENVELOPE" in items:
            envelope = self._format_envelope(msg)
            response_parts.append(f"ENVELOPE {envelope}")

        if "RFC822" in items or "BODY[]" in items:
            rfc822 = self._message_to_rfc822(msg)
            response_parts.append(f"RFC822 {{{len(rfc822)}}}\r\n{rfc822}")

        if "BODY.PEEK[HEADER]" in items or "BODY[HEADER]" in items:
            headers = self._format_headers(msg)
            response_parts.append(f"BODY[HEADER] {{{len(headers)}}}\r\n{headers}")

        if "BODY.PEEK[TEXT]" in items or "BODY[TEXT]" in items:
            text = msg.content
            response_parts.append(f"BODY[TEXT] {{{len(text)}}}\r\n{text}")

        if "INTERNALDATE" in items:
            date_str = msg.received_at.strftime("%d-%b-%Y %H:%M:%S +0000")
            response_parts.append(f'INTERNALDATE "{date_str}"')

        return f"* {seq_num} FETCH ({' '.join(response_parts)})"

    def _format_envelope(self, msg: Message) -> str:
        """Formatuje envelope IMAP."""
        date = msg.received_at.strftime("%a, %d %b %Y %H:%M:%S +0000")
        subject = msg.subject.replace('"', '\\"')
        sender = msg.sender
        recipients = " ".join([f'(NIL NIL "{r}" NIL)' for r in msg.recipients])

        return (
            f'("{date}" "{subject}" '
            f'((NIL NIL "{sender}" NIL)) '  # From
            f'((NIL NIL "{sender}" NIL)) '  # Sender
            f'((NIL NIL "{sender}" NIL)) '  # Reply-To
            f'({recipients}) '  # To
            f"NIL NIL NIL "  # Cc, Bcc, In-Reply-To
            f'"{msg.message_id}")'  # Message-ID
        )

    def _message_to_rfc822(self, msg: Message) -> str:
        """Konwertuje wiadomość e-Doręczeń na format RFC822."""
        mime_msg = MIMEMultipart()
        mime_msg["From"] = msg.sender
        mime_msg["To"] = ", ".join(msg.recipients)
        mime_msg["Subject"] = msg.subject
        mime_msg["Date"] = msg.received_at.strftime("%a, %d %b %Y %H:%M:%S +0000")
        mime_msg["Message-ID"] = f"<{msg.message_id}@edoreczenia.gov.pl>"

        # Treść wiadomości
        mime_msg.attach(MIMEText(msg.content, "plain", "utf-8"))

        return mime_msg.as_string()

    def _format_headers(self, msg: Message) -> str:
        """Formatuje nagłówki wiadomości."""
        headers = [
            f"From: {msg.sender}",
            f"To: {', '.join(msg.recipients)}",
            f"Subject: {msg.subject}",
            f"Date: {msg.received_at.strftime('%a, %d %b %Y %H:%M:%S +0000')}",
            f"Message-ID: <{msg.message_id}@edoreczenia.gov.pl>",
            "MIME-Version: 1.0",
            "Content-Type: text/plain; charset=utf-8",
        ]
        return "\r\n".join(headers) + "\r\n\r\n"

    def _parse_sequence(self, sequence: str) -> list[int]:
        """Parsuje sekwencję IMAP (np. '1:5', '1,3,5', '*')."""
        indices = []

        for part in sequence.split(","):
            if ":" in part:
                start, end = part.split(":")
                start = 1 if start == "*" else int(start)
                end = len(self.messages) if end == "*" else int(end)
                indices.extend(range(start, end + 1))
            elif part == "*":
                indices.append(len(self.messages))
            else:
                indices.append(int(part))

        return sorted(set(indices))

    async def _handle_search(self, tag: str, args: str) -> None:
        """Obsługuje SEARCH."""
        if not self.authenticated or not self.selected_mailbox:
            await self._send(f"{tag} NO Not selected")
            return

        # Uproszczone wyszukiwanie - zwraca wszystkie
        indices = " ".join(str(i + 1) for i in range(len(self.messages)))
        await self._send(f"* SEARCH {indices}")
        await self._send(f"{tag} OK SEARCH completed")

    async def _handle_store(self, tag: str, args: str) -> None:
        """Obsługuje STORE - zmiana flag."""
        if not self.authenticated or not self.selected_mailbox:
            await self._send(f"{tag} NO Not selected")
            return

        parts = args.split(" ", 2)
        if len(parts) < 3:
            await self._send(f"{tag} BAD STORE requires sequence, flags, and values")
            return

        sequence = parts[0]
        action = parts[1].upper()
        flags = parts[2].strip("()")

        try:
            indices = self._parse_sequence(sequence)

            for idx in indices:
                if 1 <= idx <= len(self.messages):
                    msg = self.messages[idx - 1]

                    # Aktualizacja flag lokalnie
                    if "+FLAGS" in action:
                        for flag in flags.split():
                            if flag not in msg.flags:
                                msg.flags.append(flag)
                    elif "-FLAGS" in action:
                        for flag in flags.split():
                            if flag in msg.flags:
                                msg.flags.remove(flag)

                    # Synchronizacja z API (np. oznaczenie jako przeczytane)
                    if "\\Seen" in flags:
                        status = "READ" if "+FLAGS" in action else "UNREAD"
                        await self.api_client.update_message_status(msg.message_id, status)

                    # Odpowiedź
                    flags_str = " ".join(msg.flags)
                    await self._send(f"* {idx} FETCH (FLAGS ({flags_str}))")

            await self._send(f"{tag} OK STORE completed")

        except Exception as e:
            logger.error("Błąd STORE", error=str(e))
            await self._send(f"{tag} NO STORE failed: {e}")

    async def _handle_noop(self, tag: str, args: str) -> None:
        """Obsługuje NOOP."""
        await self._send(f"{tag} OK NOOP completed")

    async def _handle_logout(self, tag: str, args: str) -> None:
        """Obsługuje LOGOUT."""
        await self._send("* BYE IMAP4rev1 Server logging out")
        await self._send(f"{tag} OK LOGOUT completed")
        self.running = False

    async def _handle_close(self, tag: str, args: str) -> None:
        """Obsługuje CLOSE."""
        self.selected_mailbox = None
        self.messages = []
        await self._send(f"{tag} OK CLOSE completed")

    async def _handle_expunge(self, tag: str, args: str) -> None:
        """Obsługuje EXPUNGE."""
        if not self.authenticated or not self.selected_mailbox:
            await self._send(f"{tag} NO Not selected")
            return

        # Usuń wiadomości oznaczone jako \Deleted
        deleted_indices = []
        for i, msg in enumerate(self.messages):
            if "\\Deleted" in msg.flags:
                deleted_indices.append(i + 1)

        for idx in reversed(deleted_indices):
            await self._send(f"* {idx} EXPUNGE")
            self.messages.pop(idx - 1)

        await self._send(f"{tag} OK EXPUNGE completed")

    async def _handle_uid(self, tag: str, args: str) -> None:
        """Obsługuje komendy UID."""
        parts = args.split(" ", 1)
        if len(parts) < 2:
            await self._send(f"{tag} BAD UID requires command")
            return

        command = parts[0].upper()
        uid_args = parts[1]

        if command == "FETCH":
            await self._handle_fetch(tag, uid_args)
        elif command == "SEARCH":
            await self._handle_search(tag, uid_args)
        elif command == "STORE":
            await self._handle_store(tag, uid_args)
        else:
            await self._send(f"{tag} BAD Unknown UID command: {command}")


class IMAPServer:
    """Serwer IMAP proxy."""

    def __init__(self, settings: Settings, api_client: EDoreczeniaClient):
        self.settings = settings
        self.api_client = api_client
        self._server: Optional[asyncio.Server] = None

    async def start(self) -> None:
        """Uruchamia serwer IMAP."""
        self._server = await asyncio.start_server(
            self._handle_client,
            self.settings.imap_host,
            self.settings.imap_port,
        )

        addr = self._server.sockets[0].getsockname()
        logger.info("Serwer IMAP uruchomiony", host=addr[0], port=addr[1])

        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        """Zatrzymuje serwer."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Serwer IMAP zatrzymany")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Obsługuje nowe połączenie klienta."""
        session = IMAPSession(reader, writer, self.api_client, self.settings)
        await session.handle()
