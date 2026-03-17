from __future__ import annotations

from .applescript import quote_applescript


def _message_json_fragment(message_ref: str) -> str:
    return (
        f'"{{\\\\\\"subject\\\\\\":\\\\\\"" & my esc(subject of {message_ref} as string) & "\\\\",'
        f'\\\\\\"sender\\\\\\":\\\\\\"" & my esc(sender of {message_ref} as string) & "\\\\",'
        f'\\\\\\"messageId\\\\\\":\\\\\\"" & my esc(message id of {message_ref} as string) & "\\\\",'
        f'\\\\\\"read\\\\\\":" & ((read status of {message_ref}) as string) & "}}"'
    )


def _escape_handlers() -> str:
    return """
on esc(valueText)
    set valueText to my replaceText("\\\\", "\\\\\\\\", valueText)
    set valueText to my replaceText("\\"", "\\\\\\"", valueText)
    set valueText to my replaceText(return, "\\\\n", valueText)
    set valueText to my replaceText(linefeed, "\\\\n", valueText)
    return valueText
end esc

on replaceText(findText, replaceText, sourceText)
    set AppleScript's text item delimiters to findText
    set textItems to every text item of sourceText
    set AppleScript's text item delimiters to replaceText
    set sourceText to textItems as string
    set AppleScript's text item delimiters to ""
    return sourceText
end replaceText
""".strip()


def accounts_script() -> str:
    return """
tell application "Mail"
    set output to "["
    set isFirst to true
    repeat with acct in every account
        if isFirst is false then
            set output to output & ","
        end if
        set output to output & "{\\"name\\":\\"" & (name of acct as string) & "\\",\\"id\\":\\"" & (id of acct as string) & "\\"}"
        set isFirst to false
    end repeat
    set output to output & "]"
    return output
end tell
""".strip()


def mailboxes_script() -> str:
    return """
tell application "Mail"
    set output to "["
    set isFirst to true
    repeat with box in every mailbox
        set accountName to ""
        try
            set accountName to (name of (account of box) as string)
        on error
            set accountName to ""
        end try
        if isFirst is false then
            set output to output & ","
        end if
        set output to output & "{\\"name\\":\\"" & (name of box as string) & "\\",\\"account\\":\\"" & accountName & "\\"}"
        set isFirst to false
    end repeat
    set output to output & "]"
    return output
end tell
""".strip()


def account_mailboxes_script() -> str:
    return """
tell application "Mail"
    set output to "["
    set isFirst to true
    repeat with acct in every account
        if isFirst is false then
            set output to output & ","
        end if
        set inboxName to ""
        try
            set inboxName to name of (mailbox of acct) as string
        on error
            set inboxName to ""
        end try
        set output to output & "{\\"account\\":\\"" & (name of acct as string) & "\\",\\"inbox\\":\\"" & inboxName & "\\"}"
        set isFirst to false
    end repeat
    set output to output & "]"
    return output
end tell
""".strip()


def search_messages_script(mailbox: str, query: str, limit: int) -> str:
    mailbox_value = quote_applescript(mailbox)
    return f"""
tell application "Mail"
    set targetMailbox to first mailbox whose name is {mailbox_value}
    set matchedMessages to (every message of targetMailbox whose {query})
    set maxCount to {limit}
    set output to "["
    set isFirst to true
    set currentIndex to 0
    repeat with msg in matchedMessages
        set currentIndex to currentIndex + 1
        if currentIndex is greater than maxCount then
            exit repeat
        end if
        if isFirst is false then
            set output to output & ","
        end if
        set output to output & {_message_json_fragment("msg")}
        set isFirst to false
    end repeat
    set output to output & "]"
    return output
end tell

{_escape_handlers()}
""".strip()


def list_messages_script(mailbox: str, limit: int) -> str:
    mailbox_value = quote_applescript(mailbox)
    return f"""
tell application "Mail"
    set targetMailbox to first mailbox whose name is {mailbox_value}
    set mailboxMessages to messages of targetMailbox
    set maxCount to {limit}
    set output to "["
    set isFirst to true
    set currentIndex to 0
    repeat with msg in mailboxMessages
        set currentIndex to currentIndex + 1
        if currentIndex is greater than maxCount then
            exit repeat
        end if
        if isFirst is false then
            set output to output & linefeed
        end if
        set output to output & my esc(subject of msg as string) & "|||" & my esc(sender of msg as string) & "|||" & my esc(message id of msg as string) & "|||" & ((read status of msg) as string)
        set isFirst to false
    end repeat
    return output
end tell

{_escape_handlers()}
""".strip()


def list_account_inbox_messages_script(account_name: str, limit: int) -> str:
    return list_account_mailbox_messages_script(account_name=account_name, mailbox_name="INBOX", limit=limit)


def list_account_mailbox_messages_script(account_name: str, mailbox_name: str, limit: int) -> str:
    account_value = quote_applescript(account_name)
    mailbox_value = quote_applescript(mailbox_name)
    return f"""
tell application "Mail"
    set targetAccount to first account whose name is {account_value}
    set targetMailbox to first mailbox of targetAccount whose name is {mailbox_value}
    set mailboxMessages to messages of targetMailbox
    set maxCount to {limit}
    set output to ""
    set isFirst to true
    set currentIndex to 0
    repeat with msg in mailboxMessages
        set currentIndex to currentIndex + 1
        if currentIndex is greater than maxCount then
            exit repeat
        end if
        if isFirst is false then
            set output to output & linefeed
        end if
        set output to output & my esc(subject of msg as string) & "|||" & my esc(sender of msg as string) & "|||" & my esc(message id of msg as string) & "|||" & ((read status of msg) as string) & "|||" & my joinRecipients(to recipients of msg) & "|||" & my joinRecipients(cc recipients of msg) & "|||" & (currentIndex as string) & "|||" & my esc({account_value}) & "|||" & my esc({mailbox_value})
        set isFirst to false
    end repeat
    return output
end tell

on joinRecipients(recipientList)
    set joined to ""
    set isFirst to true
    repeat with rec in recipientList
        set recAddress to ""
        try
            set recAddress to (address of rec as string)
        end try
        if recAddress is not "" then
            if isFirst is false then
                set joined to joined & ";"
            end if
            set joined to joined & my esc(recAddress)
            set isFirst to false
        end if
    end repeat
    return joined
end joinRecipients

{_escape_handlers()}
""".strip()


def list_outgoing_messages_script(limit: int) -> str:
    return f"""
tell application "Mail"
    set mailboxMessages to outgoing messages
    set maxCount to {limit}
    set output to ""
    set isFirst to true
    set currentIndex to 0
    repeat with msg in mailboxMessages
        set currentIndex to currentIndex + 1
        if currentIndex is greater than maxCount then
            exit repeat
        end if
        if isFirst is false then
            set output to output & linefeed
        end if
        set output to output & (id of msg as string) & "|||" & my esc(subject of msg as string) & "|||" & my esc(content of msg as string)
        set isFirst to false
    end repeat
    return output
end tell

{_escape_handlers()}
""".strip()


def read_message_script(message_id: str) -> str:
    message_id_value = quote_applescript(message_id)
    return f"""
tell application "Mail"
    set targetMessage to missing value
    repeat with box in every mailbox
        try
            set targetMessage to first message of box whose message id is {message_id_value}
            exit repeat
        end try
    end repeat
    if targetMessage is missing value then
        error "Message not found"
    end if
    set output to "{{\\"subject\\":\\"" & my esc(subject of targetMessage as string) & "\\",\\"sender\\":\\"" & my esc(sender of targetMessage as string) & "\\",\\"messageId\\":\\"" & my esc(message id of targetMessage as string) & "\\",\\"content\\":\\"" & my esc(content of targetMessage as string) & "\\"}}"
    return output
end tell

{_escape_handlers()}
""".strip()


def message_source_script(message_id: str) -> str:
    message_id_value = quote_applescript(message_id)
    return f"""
tell application "Mail"
    set targetMessage to missing value
    repeat with box in every mailbox
        try
            set targetMessage to first message of box whose message id is {message_id_value}
            exit repeat
        end try
    end repeat
    if targetMessage is missing value then
        error "Message not found"
    end if
    return my esc(source of targetMessage as string)
end tell

{_escape_handlers()}
""".strip()


def mailbox_message_source_script(account_name: str, mailbox_name: str, message_index: int) -> str:
    account_value = quote_applescript(account_name)
    mailbox_value = quote_applescript(mailbox_name)
    return f"""
tell application "Mail"
    set targetAccount to first account whose name is {account_value}
    set targetMailbox to first mailbox of targetAccount whose name is {mailbox_value}
    set targetMessage to message {message_index} of targetMailbox
    return my esc(source of targetMessage as string)
end tell

{_escape_handlers()}
""".strip()


def mailbox_message_details_script(account_name: str, mailbox_name: str, message_index: int) -> str:
    account_value = quote_applescript(account_name)
    mailbox_value = quote_applescript(mailbox_name)
    return f"""
tell application "Mail"
    set targetAccount to first account whose name is {account_value}
    set targetMailbox to first mailbox of targetAccount whose name is {mailbox_value}
    set targetMessage to message {message_index} of targetMailbox
    set output to "{{\\"subject\\":\\"" & my esc(subject of targetMessage as string) & "\\",\\"sender\\":\\"" & my esc(sender of targetMessage as string) & "\\",\\"messageId\\":\\"" & my esc(message id of targetMessage as string) & "\\",\\"content\\":\\"" & my esc(content of targetMessage as string) & "\\",\\"accountName\\":\\"" & my esc({account_value}) & "\\",\\"mailboxName\\":\\"" & my esc({mailbox_value}) & "\\",\\"rowIndex\\":" & ({message_index} as string) & "}}"
    return output
end tell

{_escape_handlers()}
""".strip()


def create_draft_script(to_email: str, subject: str, body: str) -> str:
    to_value = quote_applescript(to_email)
    subject_value = quote_applescript(subject)
    body_value = quote_applescript(body)
    return f"""
tell application "Mail"
    set newMessage to make new outgoing message with properties {{subject:{subject_value}, content:{body_value} & return & return}}
    tell newMessage
        make new to recipient at end of to recipients with properties {{address:{to_value}}}
        save
    end tell
    return id of newMessage as string
end tell
""".strip()


def reply_draft_script(account_name: str, mailbox_name: str, row_index: int, body: str, reply_all: bool = False) -> str:
    account_value = quote_applescript(account_name)
    mailbox_value = quote_applescript(mailbox_name)
    body_value = quote_applescript(body)
    reply_command = "reply all" if reply_all else "reply"
    return f"""
tell application "Mail"
    set targetAccount to first account whose name is {account_value}
    set targetMailbox to first mailbox of targetAccount whose name is {mailbox_value}
    set targetMessage to message {row_index} of targetMailbox
    set replyMessage to {reply_command} targetMessage opening window no
    set content of replyMessage to {body_value} & return & return & content of replyMessage
    save replyMessage
    return id of replyMessage as string
end tell
""".strip()


def send_draft_script(draft_id: str) -> str:
    draft_id_value = quote_applescript(draft_id)
    return f"""
tell application "Mail"
    set targetMessage to first outgoing message whose id is {draft_id_value}
    send targetMessage
    return id of targetMessage as string
end tell
""".strip()
