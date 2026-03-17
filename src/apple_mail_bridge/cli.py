from __future__ import annotations

import argparse
import json

from .api_contract import exception_response, normalize_command_result
from .service import AppleMailService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apple Mail bridge prototype")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("accounts")
    subparsers.add_parser("mailboxes")
    subparsers.add_parser("account-mailboxes")

    list_parser = subparsers.add_parser("list-messages")
    list_parser.add_argument("--mailbox", required=True)
    list_parser.add_argument("--limit", type=int, default=10)

    account_list_parser = subparsers.add_parser("list-account-inbox")
    account_list_parser.add_argument("--account", required=True)
    account_list_parser.add_argument("--limit", type=int, default=10)

    mailbox_list_parser = subparsers.add_parser("list-account-mailbox")
    mailbox_list_parser.add_argument("--account", required=True)
    mailbox_list_parser.add_argument("--mailbox", required=True)
    mailbox_list_parser.add_argument("--limit", type=int, default=10)

    outgoing_parser = subparsers.add_parser("list-drafts")
    outgoing_parser.add_argument("--limit", type=int, default=10)

    recipient_parser = subparsers.add_parser("find-recipient")
    recipient_parser.add_argument("--query", required=True)
    recipient_parser.add_argument("--per-account-limit", type=int, default=100)
    recipient_parser.add_argument("--max-results", type=int, default=5)
    recipient_parser.add_argument("--mode", choices=["quick", "full"], default="quick")

    refresh_parser = subparsers.add_parser("refresh-recipient-index")
    refresh_parser.add_argument("--per-account-limit", type=int, default=100)
    refresh_parser.add_argument("--mode", choices=["quick", "full"], default="quick")

    subparsers.add_parser("recipient-index-status")
    subparsers.add_parser("preflight-health")

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--mailbox", required=True)
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--limit", type=int, default=10)

    read_parser = subparsers.add_parser("read")
    read_parser.add_argument("--message-id", required=True)

    read_mailbox_parser = subparsers.add_parser("read-mailbox-message")
    read_mailbox_parser.add_argument("--account", required=True)
    read_mailbox_parser.add_argument("--mailbox", required=True)
    read_mailbox_parser.add_argument("--row-index", type=int, required=True)

    read_unread_parser = subparsers.add_parser("read-latest-unread")
    read_unread_parser.add_argument("--account", default="Google")
    read_unread_parser.add_argument("--limit", type=int, default=5)
    read_unread_parser.add_argument("--scan-limit", type=int, default=25)
    read_unread_parser.add_argument("--scope", choices=["all", "unread"], default="unread")

    list_unread_parser = subparsers.add_parser("list-latest-unread")
    list_unread_parser.add_argument("--account", default="Google")
    list_unread_parser.add_argument("--limit", type=int, default=5)
    list_unread_parser.add_argument("--scan-limit", type=int, default=25)
    list_unread_parser.add_argument("--query", default=None)
    list_unread_parser.add_argument("--scope", choices=["all", "unread"], default="unread")

    read_from_parser = subparsers.add_parser("read-latest-from")
    read_from_parser.add_argument("--query", required=True)
    read_from_parser.add_argument("--account", default="Google")
    read_from_parser.add_argument("--limit", type=int, default=5)
    read_from_parser.add_argument("--scan-limit", type=int, default=25)
    read_from_parser.add_argument("--mode", choices=["quick", "full"], default="quick")
    read_from_parser.add_argument("--scope", choices=["all", "unread"], default="unread")

    draft_parser = subparsers.add_parser("create-draft")
    draft_parser.add_argument("--to", required=True)
    draft_parser.add_argument("--subject", required=True)
    draft_parser.add_argument("--body", required=True)

    draft_recipient_parser = subparsers.add_parser("create-draft-for-recipient")
    draft_recipient_parser.add_argument("--query", required=True)
    draft_recipient_parser.add_argument("--subject", required=True)
    draft_recipient_parser.add_argument("--body", required=True)
    draft_recipient_parser.add_argument("--per-account-limit", type=int, default=100)
    draft_recipient_parser.add_argument("--mode", choices=["quick", "full"], default="quick")

    reply_parser = subparsers.add_parser("reply-email")
    reply_parser.add_argument("--account", required=True)
    reply_parser.add_argument("--mailbox", default="INBOX")
    reply_parser.add_argument("--row-index", type=int, required=True)
    reply_parser.add_argument("--body", required=True)
    reply_parser.add_argument("--reply-all", action="store_true")

    send_parser = subparsers.add_parser("send-draft")
    send_parser.add_argument("--draft-id", required=True)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    service = AppleMailService()
    try:
        if args.command == "accounts":
            result = service.list_accounts()
        elif args.command == "mailboxes":
            result = service.list_mailboxes()
        elif args.command == "account-mailboxes":
            result = service.list_account_mailboxes()
        elif args.command == "list-messages":
            result = service.list_messages(mailbox=args.mailbox, limit=args.limit)
        elif args.command == "list-account-inbox":
            result = service.list_account_inbox_messages(account_name=args.account, limit=args.limit)
        elif args.command == "list-account-mailbox":
            result = service.list_account_mailbox_messages(
                account_name=args.account,
                mailbox_name=args.mailbox,
                limit=args.limit,
            )
        elif args.command == "list-drafts":
            result = service.list_outgoing_messages(limit=args.limit)
        elif args.command == "find-recipient":
            result = service.find_recipient(
                query=args.query,
                per_account_limit=args.per_account_limit,
                max_results=args.max_results,
                mode=args.mode,
            )
        elif args.command == "refresh-recipient-index":
            result = service.refresh_recipient_index(
                per_account_limit=args.per_account_limit,
                mode=args.mode,
            )
        elif args.command == "recipient-index-status":
            result = service.recipient_index_status()
        elif args.command == "preflight-health":
            result = service.preflight_health()
        elif args.command == "search":
            result = service.search_messages(mailbox=args.mailbox, query=args.query, limit=args.limit)
        elif args.command == "read":
            result = service.read_message(message_id=args.message_id)
        elif args.command == "read-mailbox-message":
            result = service.read_mailbox_message(
                account_name=args.account,
                mailbox_name=args.mailbox,
                row_index=args.row_index,
            )
        elif args.command == "read-latest-unread":
            result = service.read_latest_unread(
                account_name=args.account,
                limit=args.limit,
                scan_limit=args.scan_limit,
                scope=args.scope,
            )
        elif args.command == "list-latest-unread":
            result = service.list_latest_unread(
                account_name=args.account,
                limit=args.limit,
                scan_limit=args.scan_limit,
                query=args.query,
                scope=args.scope,
            )
        elif args.command == "read-latest-from":
            result = service.read_latest_from(
                query=args.query,
                account_name=args.account,
                limit=args.limit,
                scan_limit=args.scan_limit,
                mode=args.mode,
                scope=args.scope,
            )
        elif args.command == "create-draft":
            draft = service.create_draft(to_email=args.to, subject=args.subject, body=args.body)
            result = service.build_direct_draft_payload(
                to_email=args.to,
                subject=args.subject,
                body=args.body,
                draft_id=draft.draft_id,
            )
        elif args.command == "create-draft-for-recipient":
            result = service.create_draft_for_recipient(
                query=args.query,
                subject=args.subject,
                body=args.body,
                per_account_limit=args.per_account_limit,
                mode=args.mode,
            )
        elif args.command == "reply-email":
            draft = service.reply_draft(
                account_name=args.account,
                mailbox_name=args.mailbox,
                row_index=args.row_index,
                body=args.body,
                reply_all=args.reply_all,
            )
            result = service.build_reply_draft_payload(
                account_name=args.account,
                mailbox_name=args.mailbox,
                row_index=args.row_index,
                body=args.body,
                draft_id=draft.draft_id,
                reply_all=args.reply_all,
            )
        elif args.command == "send-draft":
            send_result = service.send_draft(draft_id=args.draft_id)
            result = service.build_send_draft_payload(
                draft_id=send_result.draft_id,
                status=send_result.status,
            )
        else:
            parser.error(f"Unsupported command: {args.command}")
            return

        response = normalize_command_result(args.command, result)
        print(json.dumps(response, ensure_ascii=False, indent=2))
        if not response["success"]:
            raise SystemExit(1)
    except SystemExit:
        raise
    except Exception as exc:
        response = exception_response(args.command, exc)
        print(json.dumps(response, ensure_ascii=False, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
