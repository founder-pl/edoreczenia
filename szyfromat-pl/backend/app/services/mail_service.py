"""
Mail Service - Obsługa SMTP/IMAP dla e-Doręczeń
"""
import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from email.utils import formataddr
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class MailConfig:
    """Konfiguracja serwera mail"""
    SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
    IMAP_HOST = os.getenv("IMAP_HOST", "localhost")
    IMAP_PORT = int(os.getenv("IMAP_PORT", "1143"))
    MAIL_USER = os.getenv("MAIL_USER", "demo@szyfromat.pl")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "demo123")


class MailService:
    """Serwis do wysyłania i odbierania wiadomości przez SMTP/IMAP"""
    
    def __init__(self):
        self.config = MailConfig()
    
    # ═══════════════════════════════════════════════════════════════
    # SMTP - Wysyłanie wiadomości
    # ═══════════════════════════════════════════════════════════════
    
    def send_message(
        self,
        to_address: str,
        subject: str,
        body: str,
        from_address: str = None,
        attachments: List[Dict] = None,
        html_body: str = None
    ) -> Dict[str, Any]:
        """Wyślij wiadomość przez SMTP"""
        try:
            from_addr = from_address or self.config.MAIL_USER
            
            # Utwórz wiadomość
            if html_body:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(body, "plain", "utf-8"))
                msg.attach(MIMEText(html_body, "html", "utf-8"))
            else:
                msg = MIMEMultipart()
                msg.attach(MIMEText(body, "plain", "utf-8"))
            
            msg["From"] = from_addr
            msg["To"] = to_address
            msg["Subject"] = Header(subject, "utf-8")
            msg["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
            msg["Message-ID"] = f"<{uuid.uuid4().hex}@szyfromat.pl>"
            
            # Dodaj nagłówki e-Doreczenia (bez polskich znaków w nazwach)
            msg["X-eDelivery-Type"] = "official"
            msg["X-eDelivery-Sender"] = from_addr
            msg["X-eDelivery-Recipient"] = to_address
            
            # Załączniki
            if attachments:
                for att in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(att.get("content", b""))
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={att.get('filename', 'attachment')}"
                    )
                    msg.attach(part)
            
            # Wyślij
            with smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORT) as server:
                server.sendmail(from_addr, [to_address], msg.as_bytes())
            
            logger.info(f"Message sent to {to_address}")
            
            return {
                "status": "sent",
                "message_id": msg["Message-ID"],
                "to": to_address,
                "subject": subject,
                "sent_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    # ═══════════════════════════════════════════════════════════════
    # IMAP - Odbieranie wiadomości
    # ═══════════════════════════════════════════════════════════════
    
    def fetch_messages(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Pobierz wiadomości z Mailpit API (lub IMAP jako fallback)"""
        messages = []
        
        # Najpierw spróbuj Mailpit API (HTTP)
        try:
            import requests
            mailpit_api = f"http://{self.config.SMTP_HOST}:8025/api/v1/messages"
            response = requests.get(mailpit_api, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                for msg in data.get("messages", [])[:limit]:
                    # Parsuj From
                    from_data = msg.get("From", {})
                    from_addr = from_data.get("Address", "") if isinstance(from_data, dict) else str(from_data)
                    
                    # Parsuj To
                    to_list = msg.get("To", [])
                    to_addr = to_list[0].get("Address", "") if to_list and isinstance(to_list, list) else ""
                    
                    # Parsuj załączniki
                    attachments = msg.get("Attachments", []) or []
                    if isinstance(attachments, int):
                        attachments = []
                    
                    messages.append({
                        "id": f"msg-{msg.get('ID', '')}",
                        "uid": msg.get("ID", ""),
                        "message_id": msg.get("MessageID", ""),
                        "subject": msg.get("Subject", ""),
                        "from": from_addr,
                        "to": to_addr,
                        "date": msg.get("Created", datetime.utcnow().isoformat()),
                        "body": msg.get("Snippet", ""),
                        "attachments": [{"filename": a.get("FileName", ""), "size": a.get("Size", 0)} for a in attachments if isinstance(a, dict)]
                    })
                logger.info(f"Fetched {len(messages)} messages from Mailpit API")
                return messages
        except Exception as e:
            logger.warning(f"Mailpit API unavailable: {e}")
        
        # Fallback do IMAP
        try:
            imap = imaplib.IMAP4(self.config.IMAP_HOST, self.config.IMAP_PORT)
            
            try:
                imap.login(self.config.MAIL_USER, self.config.MAIL_PASSWORD)
            except:
                pass
            
            imap.select(folder)
            
            search_criteria = "UNSEEN" if unread_only else "ALL"
            _, message_numbers = imap.search(None, search_criteria)
            
            for num in message_numbers[0].split()[-limit:]:
                _, msg_data = imap.fetch(num, "(RFC822)")
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        messages.append(self._parse_message(msg, num.decode()))
            
            imap.close()
            imap.logout()
            
        except Exception as e:
            logger.error(f"Failed to fetch messages from IMAP: {e}")
        
        return messages
    
    def _parse_message(self, msg: email.message.Message, uid: str) -> Dict[str, Any]:
        """Parsuj wiadomość email"""
        # Dekoduj nagłówki
        subject = self._decode_header(msg.get("Subject", ""))
        from_addr = self._decode_header(msg.get("From", ""))
        to_addr = self._decode_header(msg.get("To", ""))
        date_str = msg.get("Date", "")
        
        # Parsuj datę
        try:
            date = email.utils.parsedate_to_datetime(date_str)
        except:
            date = datetime.utcnow()
        
        # Pobierz treść
        body = ""
        html_body = ""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if "attachment" in content_disposition:
                    attachments.append({
                        "filename": part.get_filename() or "attachment",
                        "content_type": content_type,
                        "size": len(part.get_payload(decode=True) or b"")
                    })
                elif content_type == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                elif content_type == "text/html":
                    html_body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
        else:
            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        
        return {
            "id": f"msg-{uid}",
            "uid": uid,
            "message_id": msg.get("Message-ID", ""),
            "subject": subject,
            "from": from_addr,
            "to": to_addr,
            "date": date.isoformat(),
            "body": body,
            "html_body": html_body,
            "attachments": attachments,
            "headers": {
                "x_edoreczenia_type": msg.get("X-eDoręczenia-Type", ""),
                "x_edoreczenia_sender": msg.get("X-eDoręczenia-Sender", ""),
            }
        }
    
    def _decode_header(self, header: str) -> str:
        """Dekoduj nagłówek email"""
        if not header:
            return ""
        
        decoded_parts = email.header.decode_header(header)
        result = []
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(encoding or "utf-8", errors="ignore"))
            else:
                result.append(part)
        
        return " ".join(result)
    
    def get_folders(self) -> List[str]:
        """Pobierz listę folderów (Mailpit ma tylko INBOX)"""
        # Mailpit nie obsługuje folderów - zwróć standardowe
        return ["INBOX", "Sent", "Drafts", "Trash"]
    
    def mark_as_read(self, uid: str, folder: str = "INBOX") -> bool:
        """Oznacz wiadomość jako przeczytaną"""
        try:
            imap = imaplib.IMAP4(self.config.IMAP_HOST, self.config.IMAP_PORT)
            try:
                imap.login(self.config.MAIL_USER, self.config.MAIL_PASSWORD)
            except:
                pass
            
            imap.select(folder)
            imap.store(uid.encode(), "+FLAGS", "\\Seen")
            imap.close()
            imap.logout()
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark as read: {e}")
            return False
    
    def delete_message(self, uid: str, folder: str = "INBOX") -> bool:
        """Usuń wiadomość"""
        try:
            imap = imaplib.IMAP4(self.config.IMAP_HOST, self.config.IMAP_PORT)
            try:
                imap.login(self.config.MAIL_USER, self.config.MAIL_PASSWORD)
            except:
                pass
            
            imap.select(folder)
            imap.store(uid.encode(), "+FLAGS", "\\Deleted")
            imap.expunge()
            imap.close()
            imap.logout()
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False


# Singleton
mail_service = MailService()


def seed_demo_messages():
    """Wyślij demo wiadomości do skrzynki"""
    demo_messages = [
        {
            "to": "demo@szyfromat.pl",
            "from": "urzad.skarbowy@gov.pl",
            "subject": "Wezwanie do złożenia wyjaśnień - PIT-36",
            "body": """Szanowny Podatniku,

W związku z prowadzonym postępowaniem podatkowym wzywamy do złożenia wyjaśnień 
dotyczących zeznania PIT-36 za rok 2023.

Prosimy o kontakt w terminie 14 dni od otrzymania niniejszego pisma.

Z poważaniem,
Urząd Skarbowy w Warszawie"""
        },
        {
            "to": "demo@szyfromat.pl",
            "from": "zus@zus.gov.pl",
            "subject": "Informacja o stanie konta ubezpieczonego",
            "body": """Szanowny Ubezpieczony,

Przesyłamy informację o stanie Twojego konta w ZUS za rok 2024.

Składki emerytalne: 45 678,90 PLN
Składki rentowe: 12 345,67 PLN

Szczegóły dostępne na PUE ZUS.

Z poważaniem,
Zakład Ubezpieczeń Społecznych"""
        },
        {
            "to": "demo@szyfromat.pl",
            "from": "krs@ms.gov.pl",
            "subject": "Potwierdzenie wpisu do KRS",
            "body": """Szanowni Państwo,

Informujemy o dokonaniu wpisu do Krajowego Rejestru Sądowego.

Numer KRS: 0000123456
Data wpisu: 2024-01-15

Dokument wpisu w załączniku.

Z poważaniem,
Ministerstwo Sprawiedliwości"""
        }
    ]
    
    service = MailService()
    
    for msg in demo_messages:
        result = service.send_message(
            to_address=msg["to"],
            subject=msg["subject"],
            body=msg["body"],
            from_address=msg["from"]
        )
        logger.info(f"Demo message sent: {result}")
    
    return len(demo_messages)
