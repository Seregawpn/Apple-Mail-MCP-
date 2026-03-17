from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .applescript import run_applescript, run_json_script
from .recipient_index import RecipientIndexStore
from .recipient_resolver import extract_addresses_from_source, parse_address, resolve_candidates
from . import scripts


@dataclass(frozen=True)
class DraftResult:
    draft_id: str


@dataclass(frozen=True)
class SendResult:
    draft_id: str
    status: str


class AppleMailService:
    """Single owner for all Apple Mail bridge operations."""

    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        self._recipient_index = RecipientIndexStore(project_root)

    def list_accounts(self):
        return run_json_script(scripts.accounts_script())

    def preflight_health(self) -> dict:
        checks = {
            "intent": "preflight_health",
            "mailAppAvailable": False,
            "automationPermission": False,
            "mailboxesAccessible": False,
            "recipientIndexAvailable": False,
            "ready": False,
        }
        try:
            accounts = self.list_accounts()
            checks["mailAppAvailable"] = True
            checks["automationPermission"] = True
            checks["mailboxesAccessible"] = isinstance(accounts, list)
        except Exception as exc:
            checks["status"] = "not_ready"
            checks["message"] = f"Mail preflight failed: {exc}"
            return checks

        index_meta = self.recipient_index_status()
        checks["recipientIndexAvailable"] = bool(index_meta.get("exists"))
        checks["ready"] = (
            checks["mailAppAvailable"]
            and checks["automationPermission"]
            and checks["mailboxesAccessible"]
        )
        checks["status"] = "ok" if checks["ready"] else "not_ready"
        checks["index"] = index_meta
        return checks

    def _default_account_descriptor(self) -> dict:
        return {
            "selection": "mail_app_default",
            "name": None,
        }

    def _parse_message_rows(self, output: str) -> list[dict]:
        if not output:
            return []

        messages = []
        for line in output.splitlines():
            parts = line.split("|||")
            if len(parts) != 9:
                continue
            subject, sender, message_id, read_value, to_recipients, cc_recipients, row_index, account_name, mailbox_name = parts
            messages.append(
                {
                    "subject": subject,
                    "sender": sender,
                    "messageId": message_id,
                    "read": read_value.lower() == "true",
                    "toRecipients": [item for item in to_recipients.split(";") if item],
                    "ccRecipients": [item for item in cc_recipients.split(";") if item],
                    "rowIndex": int(row_index),
                    "accountName": account_name,
                    "mailboxName": mailbox_name,
                }
            )
        return messages

    def list_mailboxes(self):
        return run_json_script(scripts.mailboxes_script())

    def list_account_mailboxes(self):
        return run_json_script(scripts.account_mailboxes_script())

    def search_messages(self, mailbox: str, query: str, limit: int = 10):
        return run_json_script(scripts.search_messages_script(mailbox=mailbox, query=query, limit=limit))

    def list_messages(self, mailbox: str, limit: int = 10):
        output = run_applescript(scripts.list_messages_script(mailbox=mailbox, limit=limit))
        return self._parse_message_rows(output)

    def list_account_inbox_messages(self, account_name: str, limit: int = 10):
        output = run_applescript(scripts.list_account_inbox_messages_script(account_name=account_name, limit=limit))
        return self._parse_message_rows(output)

    def list_account_mailbox_messages(self, account_name: str, mailbox_name: str, limit: int = 10):
        output = run_applescript(
            scripts.list_account_mailbox_messages_script(
                account_name=account_name,
                mailbox_name=mailbox_name,
                limit=limit,
            )
        )
        return self._parse_message_rows(output)

    def list_outgoing_messages(self, limit: int = 10):
        output = run_applescript(scripts.list_outgoing_messages_script(limit=limit))
        if not output:
            return []

        messages = []
        for line in output.splitlines():
            parts = line.split("|||")
            if len(parts) != 3:
                continue
            draft_id, subject, content = parts
            messages.append(
                {
                    "draftId": draft_id,
                    "subject": subject,
                    "content": content,
                }
            )
        return messages

    def read_message(self, message_id: str):
        return run_json_script(scripts.read_message_script(message_id=message_id))

    def read_mailbox_message(self, account_name: str, mailbox_name: str, row_index: int):
        return run_json_script(
            scripts.mailbox_message_details_script(
                account_name=account_name,
                mailbox_name=mailbox_name,
                message_index=row_index,
            )
        )

    def get_message_source(self, message_id: str) -> str:
        return run_applescript(scripts.message_source_script(message_id=message_id))

    def get_mailbox_message_source(self, account_name: str, mailbox_name: str, row_index: int) -> str:
        return run_applescript(
            scripts.mailbox_message_source_script(
                account_name=account_name,
                mailbox_name=mailbox_name,
                message_index=row_index,
            )
        )

    def create_draft(self, to_email: str, subject: str, body: str) -> DraftResult:
        draft_id = run_applescript(
            scripts.create_draft_script(to_email=to_email, subject=subject, body=body)
        )
        return DraftResult(draft_id=draft_id)

    def reply_draft(
        self,
        account_name: str,
        mailbox_name: str,
        row_index: int,
        body: str,
        reply_all: bool = False,
    ) -> DraftResult:
        draft_id = run_applescript(
            scripts.reply_draft_script(
                account_name=account_name,
                mailbox_name=mailbox_name,
                row_index=row_index,
                body=body,
                reply_all=reply_all,
            )
        )
        return DraftResult(draft_id=draft_id)

    def build_direct_draft_payload(self, to_email: str, subject: str, body: str, draft_id: str) -> dict:
        return {
            "status": "draft_created",
            "intent": "send_email",
            "recipientQuery": to_email,
            "resolutionStatus": "resolved",
            "resolvedRecipient": {
                "displayName": to_email,
                "email": to_email,
            },
            "account": self._default_account_descriptor(),
            "subject": subject,
            "body": body,
            "draftId": draft_id,
        }

    def build_reply_draft_payload(
        self,
        account_name: str,
        mailbox_name: str,
        row_index: int,
        body: str,
        draft_id: str,
        reply_all: bool = False,
    ) -> dict:
        return {
            "status": "draft_created",
            "intent": "reply_email",
            "account": account_name,
            "mailbox": mailbox_name,
            "rowIndex": row_index,
            "body": body,
            "replyAll": reply_all,
            "draftId": draft_id,
        }

    def send_draft(self, draft_id: str) -> SendResult:
        sent_id = run_applescript(scripts.send_draft_script(draft_id=draft_id))
        return SendResult(draft_id=sent_id, status="sent")

    def build_send_draft_payload(self, draft_id: str, status: str) -> dict:
        return {
            "status": status,
            "intent": "send_email",
            "draftId": draft_id,
        }

    def find_recipient(
        self,
        query: str,
        per_account_limit: int = 100,
        max_results: int = 5,
        mode: str = "quick",
    ):
        messages = self._recipient_index.read_messages()
        matches = (
            resolve_candidates(messages=messages, query=query, max_results=max_results)
            if messages
            else resolve_candidates(
                messages=self._collect_recipient_messages(per_account_limit=per_account_limit, mode=mode),
                query=query,
                max_results=max_results,
            )
        )
        if not matches:
            return {
                "status": "not_found",
                "intent": "resolve_email_recipient",
                "recipientQuery": query,
                "resolutionStatus": "not_found",
                "matches": [],
                "resolvedRecipient": None,
                "message": "Contact not found. Please repeat the name or provide an email.",
                "index": self._recipient_index.read_meta(),
            }

        response_matches = [
            {
                "displayName": match.display_name,
                "email": match.email,
                "hitCount": match.hit_count,
                "score": match.score,
            }
            for match in matches
        ]
        status = "resolved" if len(matches) == 1 else "ambiguous"
        message = (
            f"Recipient resolved: {matches[0].display_name} <{matches[0].email}>"
            if status == "resolved"
            else "Multiple contacts found. Please уточните получателя."
        )
        return {
            "status": status,
            "intent": "resolve_email_recipient",
            "recipientQuery": query,
            "resolutionStatus": status,
            "matches": response_matches,
            "resolvedRecipient": response_matches[0] if status == "resolved" else None,
            "message": message,
            "index": self._recipient_index.read_meta(),
        }

    def create_draft_for_recipient(
        self,
        query: str,
        subject: str,
        body: str,
        per_account_limit: int = 100,
        mode: str = "quick",
    ):
        resolution = self.find_recipient(
            query=query,
            per_account_limit=per_account_limit,
            max_results=5,
            mode=mode,
        )
        if resolution["status"] != "resolved":
            return resolution

        resolved_email = resolution["matches"][0]["email"]
        draft = self.create_draft(to_email=resolved_email, subject=subject, body=body)
        return {
            "status": "draft_created",
            "intent": "send_email",
            "recipientQuery": query,
            "resolutionStatus": "resolved",
            "resolvedRecipient": resolution["matches"][0],
            "account": self._default_account_descriptor(),
            "subject": subject,
            "body": body,
            "draftId": draft.draft_id,
        }

    def refresh_recipient_index(self, per_account_limit: int = 100, mode: str = "quick") -> dict:
        messages = self._collect_recipient_messages(per_account_limit=per_account_limit, mode=mode)
        payload = self._recipient_index.write(messages)
        return {
            "status": "refreshed",
            "intent": "refresh_recipient_index",
            "path": str(self._recipient_index.index_file),
            "updatedAt": payload["updatedAt"],
            "messageCount": len(messages),
            "mode": mode,
        }

    def recipient_index_status(self) -> dict:
        return self._recipient_index.read_meta()

    def _select_inbox_messages(
        self,
        *,
        account_name: str,
        scan_limit: int,
        scope: str,
        query: str | None = None,
    ) -> list[dict]:
        messages = self.list_account_inbox_messages(account_name=account_name, limit=scan_limit)
        normalized_scope = str(scope or "unread").strip().casefold()
        if normalized_scope not in {"all", "unread"}:
            normalized_scope = "unread"
        if normalized_scope == "unread":
            messages = [message for message in messages if not message["read"]]
        if query:
            normalized_query = query.casefold().strip()
            messages = [
                message
                for message in messages
                if normalized_query in str(message.get("sender", "")).casefold()
            ]
        return messages

    def list_latest_unread(
        self,
        account_name: str,
        limit: int = 5,
        scan_limit: int = 25,
        query: str | None = None,
        scope: str = "unread",
    ):
        selected_messages = self._select_inbox_messages(
            account_name=account_name,
            scan_limit=scan_limit,
            scope=scope,
            query=query,
        )[:limit]
        return {
            "status": "ok",
            "intent": "list_latest_unread",
            "account": account_name,
            "limit": limit,
            "scanLimit": scan_limit,
            "scope": scope,
            "query": query or "",
            "count": len(selected_messages),
            "messages": selected_messages,
        }

    def read_latest_unread(
        self,
        account_name: str,
        limit: int = 5,
        scan_limit: int = 25,
        scope: str = "unread",
    ):
        unread_payload = self.list_latest_unread(
            account_name=account_name,
            limit=limit,
            scan_limit=scan_limit,
            scope=scope,
        )
        unread_messages = unread_payload["messages"]
        return {
            "status": "ok",
            "intent": "read_latest_unread",
            "account": account_name,
            "limit": limit,
            "scanLimit": scan_limit,
            "count": len(unread_messages),
            "messages": [
                self.read_mailbox_message(
                    account_name=message["accountName"],
                    mailbox_name=message["mailboxName"],
                    row_index=message["rowIndex"],
                )
                for message in unread_messages
            ],
        }

    def read_latest_from(
        self,
        query: str,
        account_name: str = "Google",
        limit: int = 5,
        scan_limit: int = 25,
        mode: str = "quick",
        scope: str = "unread",
    ):
        messages = self._select_inbox_messages(
            account_name=account_name,
            scan_limit=scan_limit,
            scope=scope,
        )
        resolution = resolve_candidates(messages=messages, query=query, max_results=5)
        if not resolution:
            return {
                "status": "not_found",
                "intent": "read_latest_from",
                "recipientQuery": query,
                "resolutionStatus": "not_found",
                "resolvedRecipient": None,
                "account": account_name,
                "limit": limit,
                "scanLimit": scan_limit,
                "scope": scope,
                "count": 0,
                "messages": [],
                "message": f"No {'unread ' if scope == 'unread' else ''}emails found from {query}.",
            }
        if len(resolution) > 1:
            return {
                "status": "ambiguous",
                "intent": "read_latest_from",
                "recipientQuery": query,
                "resolutionStatus": "ambiguous",
                "resolvedRecipient": None,
                "matches": [
                    {
                        "displayName": match.display_name,
                        "email": match.email,
                        "hitCount": match.hit_count,
                        "score": match.score,
                    }
                    for match in resolution
                ],
                "account": account_name,
                "limit": limit,
                "scanLimit": scan_limit,
                "scope": scope,
                "count": 0,
                "messages": [],
                "message": "Multiple email senders matched the query. Please уточните отправителя.",
            }

        resolved_email = resolution[0].email
        resolved_recipient = {
            "displayName": resolution[0].display_name,
            "email": resolution[0].email,
            "hitCount": resolution[0].hit_count,
            "score": resolution[0].score,
        }
        matched_messages = []
        for message in messages:
            parsed = parse_address(message.get("sender", ""))
            sender_email = parsed[1] if parsed else ""
            if sender_email == resolved_email:
                matched_messages.append(message)
            if len(matched_messages) >= limit:
                break

        return {
            "status": "ok",
            "intent": "read_latest_from",
            "recipientQuery": query,
            "resolutionStatus": "resolved",
            "resolvedRecipient": resolved_recipient,
            "account": account_name,
            "limit": limit,
            "scanLimit": scan_limit,
            "scope": scope,
            "count": len(matched_messages),
            "messages": matched_messages,
        }

    def _collect_recipient_messages(self, per_account_limit: int, mode: str) -> list[dict]:
        messages: list[dict] = []
        for account in self.list_accounts():
            account_name = account["name"]
            messages.extend(self.list_account_inbox_messages(account_name=account_name, limit=per_account_limit))
            sent_messages = self.list_account_mailbox_messages(
                account_name=account_name,
                mailbox_name="Sent Mail",
                limit=min(per_account_limit, 20 if mode == "quick" else 50),
            )
            messages.extend(self._enrich_messages_with_source_recipients(sent_messages))
            if mode == "full":
                all_mail_messages = self.list_account_mailbox_messages(
                    account_name=account_name,
                    mailbox_name="All Mail",
                    limit=min(per_account_limit, 25),
                )
                messages.extend(self._enrich_messages_with_source_recipients(all_mail_messages))
        return messages

    def _enrich_messages_with_source_recipients(self, messages: list[dict]) -> list[dict]:
        enriched: list[dict] = []
        for message in messages:
            if message["toRecipients"] or message["ccRecipients"]:
                enriched.append(message)
                continue

            source = self.get_mailbox_message_source(
                account_name=message["accountName"],
                mailbox_name=message["mailboxName"],
                row_index=message["rowIndex"],
            )
            extracted = extract_addresses_from_source(source)
            updated = dict(message)
            if extracted["from"] and not updated.get("sender"):
                updated["sender"] = extracted["from"][0]
            updated["toRecipients"] = extracted["to"]
            updated["ccRecipients"] = extracted["cc"]
            enriched.append(updated)
        return enriched
