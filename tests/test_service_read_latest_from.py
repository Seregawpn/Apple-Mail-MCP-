from unittest.mock import patch

from apple_mail_bridge.service import AppleMailService


def test_read_latest_from_reads_by_sender_without_recipient_resolution() -> None:
    service = AppleMailService()

    with patch.object(
        service,
        "find_recipient",
        side_effect=AssertionError("read_latest_from must not use recipient resolution"),
    ), patch.object(
        service,
        "list_account_inbox_messages",
        return_value=[
            {
                "subject": "Quarterly update",
                "sender": "OpenAI <team@openai.com>",
                "messageId": "mid-1",
                "read": False,
                "rowIndex": 7,
                "accountName": "Google",
                "mailboxName": "INBOX",
            },
            {
                "subject": "Other",
                "sender": "Other Sender <other@example.com>",
                "messageId": "mid-2",
                "read": False,
                "rowIndex": 8,
                "accountName": "Google",
                "mailboxName": "INBOX",
            },
        ],
    ), patch.object(
        service,
        "read_mailbox_message",
        return_value={
            "subject": "Quarterly update",
            "sender": "OpenAI <team@openai.com>",
            "messageId": "mid-1",
            "content": "Hello from OpenAI.",
            "accountName": "Google",
            "mailboxName": "INBOX",
            "rowIndex": 7,
        },
    ):
        result = service.read_latest_from(
            query="OpenAI",
            account_name="Google",
            limit=1,
            scan_limit=5,
        )

    assert result["status"] == "ok"
    assert result["intent"] == "read_latest_from"
    assert result["resolutionStatus"] == "resolved"
    assert result["resolvedRecipient"]["email"] == "team@openai.com"
    assert result["count"] == 1
    assert result["messages"][0]["subject"] == "Quarterly update"


def test_read_latest_from_not_found_returns_email_specific_message() -> None:
    service = AppleMailService()

    with patch.object(
        service,
        "find_recipient",
        side_effect=AssertionError("read_latest_from must not use recipient resolution"),
    ), patch.object(
        service,
        "list_account_inbox_messages",
        return_value=[
            {
                "subject": "Quarterly update",
                "sender": "OpenAI <team@openai.com>",
                "messageId": "mid-1",
                "read": False,
                "rowIndex": 7,
                "accountName": "Google",
                "mailboxName": "INBOX",
            }
        ],
    ):
        result = service.read_latest_from(
            query="Audi",
            account_name="Google",
            limit=1,
            scan_limit=5,
        )

    assert result["status"] == "not_found"
    assert result["intent"] == "read_latest_from"
    assert result["resolutionStatus"] == "not_found"
    assert result["message"] == "No unread emails found from Audi."


def test_list_latest_unread_scope_all_includes_read_messages() -> None:
    service = AppleMailService()

    with patch.object(
        service,
        "list_account_inbox_messages",
        return_value=[
            {
                "subject": "Unread update",
                "sender": "OpenAI <team@openai.com>",
                "messageId": "mid-1",
                "read": False,
                "rowIndex": 7,
                "accountName": "Google",
                "mailboxName": "INBOX",
            },
            {
                "subject": "Read update",
                "sender": "OpenAI <team@openai.com>",
                "messageId": "mid-2",
                "read": True,
                "rowIndex": 8,
                "accountName": "Google",
                "mailboxName": "INBOX",
            },
        ],
    ):
        result = service.list_latest_unread(
            account_name="Google",
            limit=5,
            scan_limit=5,
            scope="all",
        )

    assert result["status"] == "ok"
    assert result["scope"] == "all"
    assert result["count"] == 2


def test_read_latest_from_scope_all_includes_read_sender_messages() -> None:
    service = AppleMailService()

    with patch.object(
        service,
        "find_recipient",
        side_effect=AssertionError("read_latest_from must not use recipient resolution"),
    ), patch.object(
        service,
        "list_account_inbox_messages",
        return_value=[
            {
                "subject": "Read sender update",
                "sender": "OpenAI <team@openai.com>",
                "messageId": "mid-1",
                "read": True,
                "rowIndex": 7,
                "accountName": "Google",
                "mailboxName": "INBOX",
            },
            {
                "subject": "Other",
                "sender": "Other Sender <other@example.com>",
                "messageId": "mid-2",
                "read": False,
                "rowIndex": 8,
                "accountName": "Google",
                "mailboxName": "INBOX",
            },
        ],
    ):
        result = service.read_latest_from(
            query="OpenAI",
            account_name="Google",
            limit=5,
            scan_limit=5,
            scope="all",
        )

    assert result["status"] == "ok"
    assert result["scope"] == "all"
    assert result["count"] == 1
    assert result["messages"][0]["subject"] == "Read sender update"
