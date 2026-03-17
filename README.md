# Apple Mail MCP

`Apple Mail MCP` is a local bridge for working with `Mail.app` on macOS.
It uses AppleScript to read mailbox data, inspect messages, resolve recipients from mail history, create drafts, create reply drafts, and send existing drafts.

This project is designed for local use on a Mac that already has Apple Mail configured with at least one mail account.

## What the project includes

- account discovery
- mailbox discovery
- inbox and mailbox message listing
- message search
- reading a message by Apple Mail message id
- reading a message by mailbox row index
- listing latest unread messages
- reading latest unread messages
- finding the latest messages from a specific sender
- recipient lookup from existing mail history
- recipient index refresh and status checks
- draft creation
- reply draft creation
- sending an existing draft
- consistent JSON output for every command

## How it works

The CLI calls `AppleMailService`, which runs AppleScript against `Mail.app`.
Every command returns a JSON envelope like this:

```json
{
  "success": true,
  "status": "ok",
  "message": "Human-readable summary",
  "data": {},
  "error": null
}
```

This makes the project usable both by humans in Terminal and by local automation tools that need a stable command contract.

## Requirements

- macOS
- Apple Mail (`Mail.app`)
- at least one mail account already connected in Apple Mail
- Python 3.10+
- permission for Terminal or your runtime to control Apple Mail via Automation

## Setup

Clone the repository and move into the project:

```bash
git clone https://github.com/Seregawpn/Apple-Mail-MCP-.git
cd Apple-Mail-MCP-
```

Create a virtual environment and install the package:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -e .
```

If you do not want to install the package, you can run it with `PYTHONPATH=src`:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli accounts
```

## First connection to Apple Mail

Before using the project:

1. Open `Mail.app` and make sure your accounts are already configured.
2. Run a health check:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli preflight-health
```

3. When macOS asks for Automation permission, allow your terminal to control Apple Mail.

Expected result:
- `mailAppAvailable: true`
- `automationPermission: true`
- `mailboxesAccessible: true`

## Basic usage

List accounts:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli accounts
```

List all mailboxes:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli mailboxes
```

List mailboxes grouped by account:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli account-mailboxes
```

List recent inbox messages for an account:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli list-account-inbox --account Google --limit 5
```

List messages from a specific mailbox:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli list-account-mailbox --account Google --mailbox "Sent Mail" --limit 5
```

Search within a mailbox:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli search --mailbox Inbox --limit 5 --query 'from contains "example.com"'
```

Read a message by Apple Mail message id:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli read --message-id "<message-id>"
```

Read a message by account, mailbox, and row index:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli read-mailbox-message --account Google --mailbox INBOX --row-index 1
```

## Unread and sender-based flows

List latest unread message previews:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli list-latest-unread --account Google --limit 5 --scan-limit 25
```

Read latest unread messages:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli read-latest-unread --account Google --limit 3 --scan-limit 25
```

Read latest messages from a sender:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli read-latest-from --account Google --query "OpenAI" --limit 3 --scan-limit 25
```

If you want to include already read messages, use `--scope all`:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli read-latest-from --account Google --query "OpenAI" --limit 3 --scan-limit 25 --scope all
```

## Recipient resolution

The project can build a lightweight recipient index from your existing mail history and use it to resolve contacts by name or email fragment.

Refresh the recipient index:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli refresh-recipient-index --mode quick --per-account-limit 20
```

Check index status:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli recipient-index-status
```

Find a recipient:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli find-recipient --mode quick --query "John Smith"
```

If multiple matches are found, the command returns `status: "ambiguous"` and the candidate list.

## Drafts and sending

Create a draft directly:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli create-draft --to test@example.com --subject "Test" --body "Hello"
```

Create a draft after resolving a recipient from mail history:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli create-draft-for-recipient --mode quick --query "John Smith" --subject "Test" --body "Hello"
```

List current drafts:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli list-drafts --limit 5
```

Create a reply draft for a message:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli reply-email --account Google --mailbox INBOX --row-index 1 --body "Thanks, received."
```

Send an existing draft:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli send-draft --draft-id "<draft-id>"
```

## Recommended quick start flow

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli preflight-health
PYTHONPATH=src python3 -m apple_mail_bridge.cli accounts
PYTHONPATH=src python3 -m apple_mail_bridge.cli refresh-recipient-index --mode quick --per-account-limit 20
PYTHONPATH=src python3 -m apple_mail_bridge.cli find-recipient --mode quick --query "John Smith"
PYTHONPATH=src python3 -m apple_mail_bridge.cli create-draft-for-recipient --mode quick --query "John Smith" --subject "Hello" --body "Test message"
PYTHONPATH=src python3 -m apple_mail_bridge.cli list-drafts --limit 5
```

## Project structure

- `src/apple_mail_bridge/cli.py`  
  Command-line entry point.
- `src/apple_mail_bridge/service.py`  
  Main service layer for all Apple Mail operations.
- `src/apple_mail_bridge/scripts.py`  
  AppleScript builders used to talk to `Mail.app`.
- `src/apple_mail_bridge/api_contract.py`  
  Response normalization and JSON contract.
- `src/apple_mail_bridge/recipient_index.py`  
  Local recipient index storage.
- `src/apple_mail_bridge/recipient_resolver.py`  
  Contact matching and recipient resolution logic.
- `src/apple_mail_bridge/applescript.py`  
  Low-level AppleScript execution helpers.

## Notes

- This project works only on macOS because it depends on `Mail.app` and AppleScript.
- It does not manage credentials directly. It uses the accounts already configured in Apple Mail.
- The safest workflow is draft-first: create a draft, inspect it in Apple Mail, then send it.
