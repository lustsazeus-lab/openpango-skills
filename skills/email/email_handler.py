#!/usr/bin/env python3
"""
Native email skill for OpenPango (IMAP/SMTP).

Implements:
- unread inbox polling (IMAP) with structured JSON parsing
- secure SMTP sending (CC/BCC/attachments)
- thread tracking via Message-ID / In-Reply-To / References
- credential integration through agent_integrations SQLite database
"""

from __future__ import annotations

import email
import imaplib
import json
import mimetypes
import os
import smtplib
import sqlite3
import time
import uuid
from contextlib import closing
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from email.utils import getaddresses, make_msgid, parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Optional


@dataclass
class EmailCredentials:
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_use_ssl: bool = False
    smtp_starttls: bool = True

    imap_host: str = ""
    imap_port: int = 993
    imap_user: str = ""
    imap_pass: str = ""
    imap_use_ssl: bool = True

    from_address: str = ""


class EmailSkillError(RuntimeError):
    pass


class EmailHandler:
    """IMAP/SMTP handler with local thread memory."""

    PROVIDER_KEY = "email"

    def __init__(
        self,
        db_path: Optional[str] = None,
        poll_interval_seconds: int = 30,
    ) -> None:
        self.db_path = Path(
            db_path
            or os.getenv(
                "OPENPANGO_AGENT_INTEGRATIONS_DB",
                str(Path.home() / ".openclaw" / "workspace" / "agent_integrations.db"),
            )
        ).expanduser()
        self.poll_interval_seconds = max(1, poll_interval_seconds)

        self._init_db()

    # --------------------------
    # Credentials / DB
    # --------------------------

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        created = not self.db_path.exists()

        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_integrations (
                    provider TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS email_thread_index (
                    message_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    normalized_subject TEXT,
                    direction TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_email_thread_subject
                ON email_thread_index(normalized_subject)
                """
            )
            conn.commit()

        if created:
            try:
                os.chmod(self.db_path, 0o600)
            except OSError:
                # Best effort on platforms/filesystems that may not support chmod.
                pass

    def save_credentials(self, credentials: EmailCredentials) -> None:
        payload = {
            "smtp_host": credentials.smtp_host,
            "smtp_port": credentials.smtp_port,
            "smtp_user": credentials.smtp_user,
            "smtp_pass": credentials.smtp_pass,
            "smtp_use_ssl": credentials.smtp_use_ssl,
            "smtp_starttls": credentials.smtp_starttls,
            "imap_host": credentials.imap_host,
            "imap_port": credentials.imap_port,
            "imap_user": credentials.imap_user,
            "imap_pass": credentials.imap_pass,
            "imap_use_ssl": credentials.imap_use_ssl,
            "from_address": credentials.from_address,
        }
        now = int(time.time())

        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO agent_integrations(provider, data_json, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(provider) DO UPDATE SET
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at
                """,
                (self.PROVIDER_KEY, json.dumps(payload), now),
            )
            conn.commit()

    def _load_db_credentials(self) -> Dict[str, Any]:
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute(
                "SELECT data_json FROM agent_integrations WHERE provider=?",
                (self.PROVIDER_KEY,),
            ).fetchone()
        if not row:
            return {}
        return json.loads(row[0])

    def _load_credentials(self) -> EmailCredentials:
        db_creds = self._load_db_credentials()

        def _get(key: str, default: Any = "") -> Any:
            env_key = f"EMAIL_{key.upper()}"
            if env_key in os.environ and os.environ[env_key] != "":
                return os.environ[env_key]
            return db_creds.get(key, default)

        creds = EmailCredentials(
            smtp_host=str(_get("smtp_host", "")).strip(),
            smtp_port=int(_get("smtp_port", 587)),
            smtp_user=str(_get("smtp_user", "")).strip(),
            smtp_pass=str(_get("smtp_pass", "")),
            smtp_use_ssl=self._to_bool(_get("smtp_use_ssl", False)),
            smtp_starttls=self._to_bool(_get("smtp_starttls", True)),
            imap_host=str(_get("imap_host", "")).strip(),
            imap_port=int(_get("imap_port", 993)),
            imap_user=str(_get("imap_user", "")).strip(),
            imap_pass=str(_get("imap_pass", "")),
            imap_use_ssl=self._to_bool(_get("imap_use_ssl", True)),
            from_address=str(_get("from_address", "")).strip(),
        )

        if not creds.smtp_host or not creds.imap_host:
            raise EmailSkillError("Missing email credentials. Save credentials in agent_integrations provider=email.")

        if not creds.smtp_user or not creds.imap_user:
            raise EmailSkillError("Missing smtp_user/imap_user in email credentials.")

        return creds

    @staticmethod
    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    # --------------------------
    # Thread tracking
    # --------------------------

    @staticmethod
    def _normalize_subject(subject: str) -> str:
        s = (subject or "").strip().lower()
        changed = True
        while changed:
            changed = False
            for prefix in ("re:", "fwd:", "fw:"):
                if s.startswith(prefix):
                    s = s[len(prefix) :].strip()
                    changed = True
        return s

    def _resolve_thread_id(
        self,
        message_id: str,
        subject: str,
        in_reply_to: Optional[str],
        references: List[str],
    ) -> str:
        norm_subject = self._normalize_subject(subject)
        resolved: Optional[str] = None

        with closing(sqlite3.connect(self.db_path)) as conn:
            for ref in [in_reply_to, *references]:
                if not ref:
                    continue
                row = conn.execute(
                    "SELECT thread_id FROM email_thread_index WHERE message_id=?",
                    (ref,),
                ).fetchone()
                if row:
                    resolved = row[0]
                    break

            if not resolved and norm_subject:
                row = conn.execute(
                    """
                    SELECT thread_id FROM email_thread_index
                    WHERE normalized_subject=?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (norm_subject,),
                ).fetchone()
                if row:
                    resolved = row[0]

        return resolved or message_id or str(uuid.uuid4())

    def _remember_message(
        self,
        message_id: str,
        thread_id: str,
        subject: str,
        direction: str,
    ) -> None:
        if not message_id:
            return
        now = int(time.time())
        norm_subject = self._normalize_subject(subject)
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO email_thread_index(message_id, thread_id, normalized_subject, direction, created_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    thread_id=excluded.thread_id,
                    normalized_subject=excluded.normalized_subject,
                    direction=excluded.direction,
                    created_at=excluded.created_at
                """,
                (message_id, thread_id, norm_subject, direction, now),
            )
            conn.commit()

    # --------------------------
    # IMAP read / polling
    # --------------------------

    def read_unread(self, folder: str = "INBOX", limit: int = 25, mark_seen: bool = False) -> List[Dict[str, Any]]:
        creds = self._load_credentials()
        limit = max(1, min(limit, 200))

        mailbox: imaplib.IMAP4
        if creds.imap_use_ssl:
            mailbox = imaplib.IMAP4_SSL(creds.imap_host, creds.imap_port)
        else:
            mailbox = imaplib.IMAP4(creds.imap_host, creds.imap_port)

        messages: List[Dict[str, Any]] = []
        try:
            mailbox.login(creds.imap_user, creds.imap_pass)
            mailbox.select(folder)

            typ, data = mailbox.search(None, "UNSEEN")
            if typ != "OK" or not data or not data[0]:
                return []

            ids = data[0].split()[-limit:]
            for msg_id in ids:
                fetch_query = "(RFC822)" if mark_seen else "(BODY.PEEK[])"
                typ, msg_data = mailbox.fetch(msg_id, fetch_query)
                if typ != "OK" or not msg_data:
                    continue

                raw_email = None
                for item in msg_data:
                    if isinstance(item, tuple) and len(item) >= 2:
                        raw_email = item[1]
                        break
                if not raw_email:
                    continue

                parsed = email.message_from_bytes(raw_email)
                item = self._to_structured_json(parsed)
                item["imap_message_id"] = msg_id.decode(errors="ignore")
                messages.append(item)

            return messages
        finally:
            try:
                mailbox.logout()
            except Exception:
                pass

    def poll_unread(
        self,
        folder: str = "INBOX",
        limit: int = 25,
        cycles: int = 1,
        sleep_seconds: Optional[int] = None,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Poll unread mail. This is the polling fallback when IMAP IDLE isn't available.
        """
        sleep_for = self.poll_interval_seconds if sleep_seconds is None else max(1, sleep_seconds)
        cycles = max(1, cycles)

        for i in range(cycles):
            yield self.read_unread(folder=folder, limit=limit)
            if i < cycles - 1:
                time.sleep(sleep_for)

    # --------------------------
    # SMTP send
    # --------------------------

    def send_email(
        self,
        to: Iterable[str],
        subject: str,
        text_body: str,
        html_body: Optional[str] = None,
        cc: Optional[Iterable[str]] = None,
        bcc: Optional[Iterable[str]] = None,
        attachments: Optional[Iterable[str]] = None,
        in_reply_to: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        creds = self._load_credentials()

        to_list = [x.strip() for x in to if str(x).strip()]
        cc_list = [x.strip() for x in (cc or []) if str(x).strip()]
        bcc_list = [x.strip() for x in (bcc or []) if str(x).strip()]
        if not to_list:
            raise EmailSkillError("At least one recipient is required")

        from_addr = creds.from_address or creds.smtp_user
        msg = EmailMessage()
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_list)
        msg["Subject"] = subject
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)

        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = in_reply_to

        message_id = make_msgid(domain=(from_addr.split("@")[-1] if "@" in from_addr else None))
        msg["Message-ID"] = message_id

        msg.set_content(text_body or "")
        if html_body:
            msg.add_alternative(html_body, subtype="html")

        attached_files: List[str] = []
        for path in attachments or []:
            file_path = Path(path).expanduser().resolve()
            if not file_path.exists() or not file_path.is_file():
                raise EmailSkillError(f"Attachment not found: {file_path}")

            ctype, _ = mimetypes.guess_type(str(file_path))
            if not ctype:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            with file_path.open("rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=file_path.name,
                )
            attached_files.append(str(file_path))

        all_recipients = to_list + cc_list + bcc_list
        if creds.smtp_use_ssl:
            server = smtplib.SMTP_SSL(creds.smtp_host, creds.smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(creds.smtp_host, creds.smtp_port, timeout=20)

        try:
            if not creds.smtp_use_ssl and creds.smtp_starttls:
                server.starttls()
            if creds.smtp_user:
                server.login(creds.smtp_user, creds.smtp_pass)
            server.send_message(msg, from_addr=from_addr, to_addrs=all_recipients)
        finally:
            try:
                server.quit()
            except Exception:
                pass

        resolved_thread = thread_id or self._resolve_thread_id(
            message_id=message_id,
            subject=subject,
            in_reply_to=in_reply_to,
            references=[in_reply_to] if in_reply_to else [],
        )
        self._remember_message(
            message_id=message_id,
            thread_id=resolved_thread,
            subject=subject,
            direction="outbound",
        )

        return {
            "status": "sent",
            "message_id": message_id,
            "thread_id": resolved_thread,
            "to": to_list,
            "cc": cc_list,
            "bcc_count": len(bcc_list),
            "attachments": attached_files,
        }

    # --------------------------
    # Parsing
    # --------------------------

    @staticmethod
    def _decode_header(value: Optional[str]) -> str:
        if not value:
            return ""
        try:
            return str(make_header(decode_header(value)))
        except Exception:
            return value

    @staticmethod
    def _extract_references(header_value: str) -> List[str]:
        if not header_value:
            return []
        refs = []
        for token in header_value.split():
            token = token.strip()
            if token.startswith("<") and token.endswith(">"):
                refs.append(token)
        return refs

    def _to_structured_json(self, msg: Message) -> Dict[str, Any]:
        message_id = (msg.get("Message-ID") or "").strip() or f"<{uuid.uuid4()}@local>"
        in_reply_to = (msg.get("In-Reply-To") or "").strip() or None
        refs = self._extract_references(msg.get("References") or "")

        subject = self._decode_header(msg.get("Subject"))
        thread_id = self._resolve_thread_id(message_id, subject, in_reply_to, refs)

        text_body = ""
        html_body = ""
        attachments: List[Dict[str, Any]] = []

        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = (part.get("Content-Disposition") or "").lower()
                content_type = (part.get_content_type() or "").lower()

                if "attachment" in content_disposition:
                    payload = part.get_payload(decode=True) or b""
                    attachments.append(
                        {
                            "filename": self._decode_header(part.get_filename() or "attachment"),
                            "content_type": content_type,
                            "size_bytes": len(payload),
                        }
                    )
                    continue

                if content_type == "text/plain" and not text_body:
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    text_body = payload.decode(charset, errors="replace")
                elif content_type == "text/html" and not html_body:
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    html_body = payload.decode(charset, errors="replace")
        else:
            payload = msg.get_payload(decode=True) or b""
            charset = msg.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if (msg.get_content_type() or "").lower() == "text/html":
                html_body = decoded
            else:
                text_body = decoded

        from_parsed = getaddresses([msg.get("From") or ""])
        to_parsed = getaddresses([msg.get("To") or ""])
        cc_parsed = getaddresses([msg.get("Cc") or ""])

        date_header = msg.get("Date")
        received_at = None
        if date_header:
            try:
                received_at = parsedate_to_datetime(date_header).isoformat()
            except Exception:
                received_at = date_header

        self._remember_message(
            message_id=message_id,
            thread_id=thread_id,
            subject=subject,
            direction="inbound",
        )

        return {
            "thread_id": thread_id,
            "message_id": message_id,
            "in_reply_to": in_reply_to,
            "references": refs,
            "subject": subject,
            "from": [{"name": n, "email": a} for n, a in from_parsed if a],
            "to": [{"name": n, "email": a} for n, a in to_parsed if a],
            "cc": [{"name": n, "email": a} for n, a in cc_parsed if a],
            "date": received_at,
            "text_body": text_body,
            "html_body": html_body,
            "attachments": attachments,
            "has_attachments": bool(attachments),
        }
