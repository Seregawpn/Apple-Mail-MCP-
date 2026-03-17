from __future__ import annotations

from typing import Any


SUCCESS_STATUSES = {
    "ok",
    "resolved",
    "draft_created",
    "refreshed",
    "sent",
}

ERROR_STATUSES = {
    "error",
    "not_found",
    "ambiguous",
}


def build_response(*, success: bool, status: str, message: str, data: Any, error: dict | None = None) -> dict:
    return {
        "success": success,
        "status": status,
        "message": message,
        "data": data,
        "error": error,
    }


def success_response(*, data: Any, status: str = "ok", message: str = "OK") -> dict:
    return build_response(success=True, status=status, message=message, data=data, error=None)


def error_response(*, status: str = "error", message: str, data: Any = None, error: dict | None = None) -> dict:
    payload_error = error or {"code": status}
    return build_response(success=False, status=status, message=message, data=data, error=payload_error)


def normalize_command_result(command: str, result: Any) -> dict:
    if isinstance(result, dict):
        status = str(result.get("status", "ok"))
        message = str(result.get("message", "")).strip()

        if command == "recipient-index-status":
            if result.get("exists"):
                return success_response(status="ok", message="Recipient index is available.", data=result)
            return error_response(status="not_ready", message="Recipient index is not built yet.", data=result)

        if command == "preflight-health":
            if status == "ok":
                return success_response(status="ok", message=message or default_message(command, "ok"), data=result)
            return error_response(status="not_ready", message=message or default_message(command, "not_ready"), data=result)

        if status in SUCCESS_STATUSES:
            return success_response(status=status, message=message or default_message(command, status), data=result)
        if status in ERROR_STATUSES:
            return error_response(status=status, message=message or default_message(command, status), data=result)

        if "draft_id" in result and "status" in result:
            status = str(result["status"])
            is_success = status in SUCCESS_STATUSES
            return build_response(
                success=is_success,
                status=status,
                message=message or default_message(command, status),
                data=result,
                error=None if is_success else {"code": status},
            )

        if "draft_id" in result:
            return success_response(status="draft_created", message=default_message(command, "draft_created"), data=result)

        return success_response(status="ok", message=message or default_message(command, "ok"), data=result)

    if isinstance(result, list):
        return success_response(
            status="ok",
            message=default_message(command, "ok"),
            data={"items": result, "count": len(result)},
        )

    return success_response(status="ok", message=default_message(command, "ok"), data={"value": result})


def exception_response(command: str, exc: Exception) -> dict:
    status = "error"
    message = f"{command} failed: {exc}"
    return error_response(status=status, message=message, error={"code": type(exc).__name__})


def default_message(command: str, status: str) -> str:
    defaults = {
        ("accounts", "ok"): "Accounts fetched successfully.",
        ("mailboxes", "ok"): "Mailboxes fetched successfully.",
        ("account-mailboxes", "ok"): "Account mailboxes fetched successfully.",
        ("list-messages", "ok"): "Messages fetched successfully.",
        ("list-account-inbox", "ok"): "Inbox messages fetched successfully.",
        ("list-account-mailbox", "ok"): "Mailbox messages fetched successfully.",
        ("list-drafts", "ok"): "Drafts fetched successfully.",
        ("search", "ok"): "Search completed successfully.",
        ("read", "ok"): "Message read successfully.",
        ("read-mailbox-message", "ok"): "Message read successfully.",
        ("list-latest-unread", "ok"): "Message previews listed successfully.",
        ("read-latest-unread", "ok"): "Unread messages read successfully.",
        ("read-latest-from", "ok"): "Message previews from sender listed successfully.",
        ("find-recipient", "resolved"): "Recipient resolved successfully.",
        ("find-recipient", "ambiguous"): "Multiple recipients matched the query.",
        ("find-recipient", "not_found"): "Recipient was not found.",
        ("create-draft", "draft_created"): "Draft created successfully.",
        ("create-draft-for-recipient", "draft_created"): "Draft created for resolved recipient.",
        ("reply-email", "draft_created"): "Reply draft created successfully.",
        ("send-draft", "sent"): "Draft sent successfully.",
        ("refresh-recipient-index", "refreshed"): "Recipient index refreshed successfully.",
        ("recipient-index-status", "ok"): "Recipient index status fetched successfully.",
        ("recipient-index-status", "not_ready"): "Recipient index is not built yet.",
        ("preflight-health", "ok"): "Mail preflight passed successfully.",
        ("preflight-health", "not_ready"): "Mail preflight is not ready.",
    }
    return defaults.get((command, status), f"{command} completed with status '{status}'.")
