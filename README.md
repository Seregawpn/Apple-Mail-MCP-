# Apple Mail MCP

Isolated sandbox for a local Apple Mail integration prototype.

Goals:
- stay out of `client/`
- stay out of `server/`
- validate a local bridge to `Mail.app` on macOS

Source of Truth:
- `Mail.app`
- mail accounts already connected inside Apple Mail

Simplified architecture:

- `service.py`
  - single owner of mail domain logic
  - fix `read/send/resolve/preflight` here
- `scripts.py`
  - single owner of AppleScript commands
  - fix locators and Mail.app selectors here
- `api_contract.py`
  - single owner of the JSON envelope
  - fix external `status/message/error` shape here
- `cli.py`
  - thin boundary only
  - mail business logic must not live here

Fast-fix rule:
- if a Mail.app action is broken, start with `service.py`, then `scripts.py`
- if the JSON response is broken, fix only `api_contract.py`
- if the CLI command is broken, fix only `cli.py`

JSON API envelope:

```json
{
  "success": true,
  "status": "ok",
  "message": "Human-readable summary",
  "data": {},
  "error": null
}
```

Rules:
- `success=true` only for terminal success states
- `success=false` for `error`, `not_found`, `ambiguous`, `not_ready`
- domain data must always live in `data`
- error details must always live in `error`

Email command contract:

- `intent`
- `recipientQuery`
- `resolutionStatus`
- `resolvedRecipient`
- `account`
- `subject`
- `body`
- `draftId`
- `messages`
- `limit`
- `scanLimit`

Current MVP scope:
- list accounts
- list mailboxes
- search messages
- read a message by id
- create a draft
- list drafts
- send an existing draft by id
- resolve a recipient from email history

Out of scope for phase one:
- automatic sending without confirmation
- backend/API integration outside the local machine
- storing tokens, passwords, or credentials

Run:

```bash
cd Apple-Mail-MCP
python3 -m apple_mail_bridge.cli accounts
python3 -m apple_mail_bridge.cli mailboxes
python3 -m apple_mail_bridge.cli account-mailboxes
python3 -m apple_mail_bridge.cli list-messages --mailbox Outbox --limit 5
python3 -m apple_mail_bridge.cli list-account-inbox --account Google --limit 5
python3 -m apple_mail_bridge.cli list-account-mailbox --account Google --mailbox "Sent Mail" --limit 5
python3 -m apple_mail_bridge.cli refresh-recipient-index --mode quick --per-account-limit 20
python3 -m apple_mail_bridge.cli recipient-index-status
python3 -m apple_mail_bridge.cli preflight-health
python3 -m apple_mail_bridge.cli find-recipient --mode quick --query "Sergiy Zasorin"
python3 -m apple_mail_bridge.cli read-latest-unread --account Google --limit 3
python3 -m apple_mail_bridge.cli read-latest-from --mode quick --account Google --query "Sergiy Zasorin"
python3 -m apple_mail_bridge.cli search --mailbox Inbox --limit 5 --query "from contains \"example.com\""
python3 -m apple_mail_bridge.cli read --message-id "<message-id>"
python3 -m apple_mail_bridge.cli create-draft --to test@example.com --subject "Test" --body "Hello"
python3 -m apple_mail_bridge.cli create-draft-for-recipient --query "Sergiy Zasorin" --subject "Test" --body "Hello"
python3 -m apple_mail_bridge.cli list-drafts --limit 5
python3 -m apple_mail_bridge.cli send-draft --draft-id "<draft-id>"
```

Environment setup:

```bash
cd Apple-Mail-MCP
PYTHONPATH=src python3 -m apple_mail_bridge.cli accounts
```

Recommended write flow:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli create-draft --to test@example.com --subject "Test" --body "Hello"
PYTHONPATH=src python3 -m apple_mail_bridge.cli list-drafts --limit 5
PYTHONPATH=src python3 -m apple_mail_bridge.cli send-draft --draft-id "<draft-id>"
```

Recommended recipient flow:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli find-recipient --mode quick --query "John Smith"
PYTHONPATH=src python3 -m apple_mail_bridge.cli create-draft-for-recipient --mode quick --query "John Smith" --subject "Test" --body "Hello"
```

Recommended quick flow:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli preflight-health
PYTHONPATH=src python3 -m apple_mail_bridge.cli refresh-recipient-index --mode quick --per-account-limit 20
PYTHONPATH=src python3 -m apple_mail_bridge.cli find-recipient --mode quick --query "John Smith"
```
