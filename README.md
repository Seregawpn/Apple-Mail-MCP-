# Apple Mail folder

Изолированный sandbox для прототипа интеграции с Apple Mail.

Цель:
- не входить в `client/`
- не входить в `server/`
- проверить локальный bridge к `Mail.app` на macOS

Source of Truth:
- `Mail.app`
- уже подключенные в нем почтовые аккаунты

Упрощенная архитектура:

- `service.py`
  - единственный owner mail-логики
  - здесь чинить `read/send/resolve/preflight`
- `scripts.py`
  - единственный owner AppleScript команд
  - здесь чинить locators и Mail.app selectors
- `api_contract.py`
  - единственный owner JSON envelope
  - здесь чинить внешние `status/message/error`
- `cli.py`
  - thin boundary only
  - здесь не должна жить mail-бизнес-логика

Правило для быстрых исправлений:
- если сломалось действие Mail.app -> сначала `service.py`, потом `scripts.py`
- если сломался JSON ответ -> только `api_contract.py`
- если сломалась команда запуска -> только `cli.py`

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

Правила:
- `success=true` только для terminal-success состояний
- `success=false` для `error`, `not_found`, `ambiguous`, `not_ready`
- доменные данные всегда лежат в `data`
- детали ошибки всегда лежат в `error`

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

Текущий объем MVP:
- список аккаунтов
- список ящиков
- поиск писем
- чтение письма по id
- создание черновика
- просмотр черновиков
- отправка существующего черновика по id
- поиск получателя по истории email

Не входит в первый этап:
- автоматическая отправка без подтверждения
- backend/API интеграция вне локальной машины
- хранение токенов, паролей и учетных данных

Запуск:

```bash
cd "Apple Mail folder"
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

Подготовка окружения:

```bash
cd "Apple Mail folder"
PYTHONPATH=src python3 -m apple_mail_bridge.cli accounts
```

Рекомендуемый write-flow:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli create-draft --to test@example.com --subject "Test" --body "Hello"
PYTHONPATH=src python3 -m apple_mail_bridge.cli list-drafts --limit 5
PYTHONPATH=src python3 -m apple_mail_bridge.cli send-draft --draft-id "<draft-id>"
```

Рекомендуемый recipient-flow:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli find-recipient --mode quick --query "John Smith"
PYTHONPATH=src python3 -m apple_mail_bridge.cli create-draft-for-recipient --mode quick --query "John Smith" --subject "Test" --body "Hello"
```

Рекомендуемый быстрый flow:

```bash
PYTHONPATH=src python3 -m apple_mail_bridge.cli preflight-health
PYTHONPATH=src python3 -m apple_mail_bridge.cli refresh-recipient-index --mode quick --per-account-limit 20
PYTHONPATH=src python3 -m apple_mail_bridge.cli find-recipient --mode quick --query "John Smith"
```
