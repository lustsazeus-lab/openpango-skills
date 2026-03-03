import importlib.util
import pathlib
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from email.message import EmailMessage
from unittest.mock import patch

MODULE_PATH = pathlib.Path(__file__).resolve().parent / "email_handler.py"
spec = importlib.util.spec_from_file_location("email_handler", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

EmailHandler = mod.EmailHandler
EmailCredentials = mod.EmailCredentials


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=20):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in = None
        self.sent = None
        self.quit_called = False
        FakeSMTP.instances.append(self)

    def starttls(self):
        self.started_tls = True

    def login(self, user, pwd):
        self.logged_in = (user, pwd)

    def send_message(self, msg, from_addr=None, to_addrs=None):
        self.sent = {
            "msg": msg,
            "from_addr": from_addr,
            "to_addrs": to_addrs,
        }

    def quit(self):
        self.quit_called = True


class FakeIMAP:
    sample_raw = b""

    def __init__(self, *args, **kwargs):
        self.logged_out = False

    def login(self, user, pwd):
        return "OK", []

    def select(self, folder):
        return "OK", [b"1"]

    def search(self, charset, criteria):
        return "OK", [b"1 2"]

    def fetch(self, msg_id, query):
        return "OK", [(b"1 (RFC822 {123})", FakeIMAP.sample_raw)]

    def logout(self):
        self.logged_out = True


class TestEmailHandler(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = pathlib.Path(self.tmp.name) / "agent_integrations.db"
        self.handler = EmailHandler(db_path=str(self.db_path), poll_interval_seconds=1)
        self.handler.save_credentials(
            EmailCredentials(
                smtp_host="smtp.test.local",
                smtp_port=587,
                smtp_user="bot@test.local",
                smtp_pass="smtp-pass",
                smtp_starttls=True,
                imap_host="imap.test.local",
                imap_port=993,
                imap_user="bot@test.local",
                imap_pass="imap-pass",
                from_address="bot@test.local",
            )
        )

    def tearDown(self):
        self.tmp.cleanup()
        FakeSMTP.instances.clear()

    def test_credentials_saved_in_agent_integrations(self):
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute(
                "SELECT provider, data_json FROM agent_integrations WHERE provider='email'"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "email")
        self.assertIn("smtp.test.local", row[1])

    @patch.object(mod.smtplib, "SMTP", FakeSMTP)
    def test_send_email_with_cc_bcc_and_attachment(self):
        attachment = pathlib.Path(self.tmp.name) / "notes.txt"
        attachment.write_text("hello attachment", encoding="utf-8")

        result = self.handler.send_email(
            to=["a@test.local"],
            cc=["cc@test.local"],
            bcc=["bcc@test.local"],
            subject="Status Update",
            text_body="Plain body",
            html_body="<p>HTML body</p>",
            attachments=[str(attachment)],
        )

        self.assertEqual(result["status"], "sent")
        self.assertTrue(result["thread_id"])
        self.assertEqual(result["bcc_count"], 1)

        smtp = FakeSMTP.instances[-1]
        self.assertTrue(smtp.started_tls)
        self.assertEqual(smtp.logged_in, ("bot@test.local", "smtp-pass"))
        self.assertIn("a@test.local", smtp.sent["to_addrs"])
        self.assertIn("cc@test.local", smtp.sent["to_addrs"])
        self.assertIn("bcc@test.local", smtp.sent["to_addrs"])

    @patch.object(mod.imaplib, "IMAP4_SSL", FakeIMAP)
    def test_read_unread_returns_structured_json_and_thread(self):
        msg = EmailMessage()
        msg["From"] = "Alice <alice@example.com>"
        msg["To"] = "bot@test.local"
        msg["Subject"] = "Re: Invoice"
        msg["Message-ID"] = "<msg-1@example.com>"
        msg["Date"] = "Tue, 03 Mar 2026 09:00:00 +0000"
        msg.set_content("Please check the invoice.")
        FakeIMAP.sample_raw = msg.as_bytes()

        items = self.handler.read_unread(limit=5)
        self.assertEqual(len(items), 2)  # fake IMAP returns 2 ids
        first = items[0]
        self.assertIn("thread_id", first)
        self.assertEqual(first["message_id"], "<msg-1@example.com>")
        self.assertEqual(first["subject"], "Re: Invoice")
        self.assertEqual(first["from"][0]["email"], "alice@example.com")

    @patch.object(mod.imaplib, "IMAP4_SSL", FakeIMAP)
    def test_thread_tracking_uses_in_reply_to(self):
        root = EmailMessage()
        root["From"] = "Alice <alice@example.com>"
        root["To"] = "bot@test.local"
        root["Subject"] = "Project Plan"
        root["Message-ID"] = "<root@example.com>"
        root.set_content("Root")
        FakeIMAP.sample_raw = root.as_bytes()
        first = self.handler.read_unread(limit=1)[0]

        reply = EmailMessage()
        reply["From"] = "Alice <alice@example.com>"
        reply["To"] = "bot@test.local"
        reply["Subject"] = "Re: Project Plan"
        reply["Message-ID"] = "<reply@example.com>"
        reply["In-Reply-To"] = "<root@example.com>"
        reply["References"] = "<root@example.com>"
        reply.set_content("Follow-up")
        FakeIMAP.sample_raw = reply.as_bytes()
        second = self.handler.read_unread(limit=1)[0]

        self.assertEqual(first["thread_id"], second["thread_id"])


if __name__ == "__main__":
    unittest.main()
