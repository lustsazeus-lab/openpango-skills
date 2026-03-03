---
name: email
description: "Native Email Management (IMAP/SMTP): poll unread inbox, send/reply with CC/BCC/attachments, and persist thread context for autonomous agents."
version: "1.0.0"
user-invocable: true
metadata:
  capabilities:
    - comms/email
    - imap/polling
    - smtp/send
    - email/thread-tracking
  author: "OpenPango Agent"
  license: "MIT"
---

# Native Email Management Skill (IMAP/SMTP)

This skill provides a focused, production-oriented email layer for autonomous agents.

## What it does

- Poll unread inbox messages over IMAP (`read_unread`, `poll_unread`)
- Parse messages into structured JSON for agent reasoning
- Send/reply with SMTP (supports `cc`, `bcc`, and file attachments)
- Track conversation threads using `Message-ID`, `In-Reply-To`, and `References`
- Store credentials in `agent_integrations` SQLite (`provider = email`)

## Credential storage

Credentials are loaded from:

1. Environment variables (`EMAIL_*`) if present
2. `agent_integrations` SQLite record for provider `email`

The handler creates/uses:

- `agent_integrations` table (credentials)
- `email_thread_index` table (thread memory)

## Example

```python
from skills.email.email_handler import EmailHandler, EmailCredentials

handler = EmailHandler()
handler.save_credentials(
    EmailCredentials(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="bot@example.com",
        smtp_pass="secret",
        imap_host="imap.example.com",
        imap_port=993,
        imap_user="bot@example.com",
        imap_pass="secret",
        from_address="bot@example.com",
    )
)

unread = handler.read_unread(limit=10)
if unread:
    first = unread[0]
    handler.send_email(
        to=["user@example.com"],
        subject=f"Re: {first['subject']}",
        text_body="Got it — I will handle this.",
        in_reply_to=first["message_id"],
        thread_id=first["thread_id"],
    )
```
