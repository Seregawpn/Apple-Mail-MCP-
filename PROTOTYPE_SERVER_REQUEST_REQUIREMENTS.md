# Apple Mail Prototype Server Request Requirements

## Purpose

Этот документ фиксирует канонический request/response contract между общим сервером и локальным mail-прототипом в `/Apple Mail folder`.

Цель:
- не создавать второй owner-path для email-логики;
- передавать в прототип уже нормализованный command payload;
- получить единый JSON envelope для `resolve`, `read`, `draft`, `send`.

## Architecture Fit

- Where it belongs: boundary между server JSON-API и `apple_mail_bridge`.
- Source of Truth:
  - сервер: владелец intent и входного command payload;
  - `apple_mail_bridge`: владелец recipient resolution, read/send workflow;
  - `Mail.app`: владелец mailbox state и реальной отправки.

Запрещено:
- искать recipient и на сервере, и в прототипе одновременно;
- отправлять письмо напрямую без `draftId`;
- передавать в прототип только сырой user text как единственный input.

## Simplicity-First Integration Model

Для адаптации в основной проект закрепляется максимально простой execution model:

1. Один transport path:
   - `server -> sync request -> sync JSON response`
2. Один send path:
   - `send_email -> draft_created -> send_draft -> sent`
3. Один owner result:
   - только response envelope прототипа
4. Один owner recipient resolution:
   - только `apple_mail_bridge`

На первом этапе не использовать:
- callback/webhook path;
- parallel async result delivery;
- server-side recipient guessing;
- direct send без draft phase.

Причина:
- так проще дебажить;
- так проще чинить поломки;
- меньше ветвлений и меньше скрытых состояний.

## Supported Intents

Прототип должен принимать только явные intents:

1. `resolve_email_recipient`
2. `send_email`
3. `send_draft`
4. `read_latest_unread`
5. `read_latest_from`
6. `refresh_recipient_index`
7. `recipient_index_status`
8. `preflight_health`

## Canonical Request Envelope

Все server requests должны приходить в одном envelope:

```json
{
  "request_id": "uuid-or-trace-id",
  "source": "server_api",
  "intent": "send_email",
  "payload": {}
}
```

Обязательные поля:
- `request_id`
- `source`
- `intent`
- `payload`

Обязательные transport rules:
- все requests синхронные;
- сервер всегда ждет один JSON response;
- `request_id` обязателен для логов и повторов;
- для send intents обязателен `idempotency_key`.

## Intent Contracts

### 1. resolve_email_recipient

Используется, когда сервер хочет заранее понять, найден ли recipient.

```json
{
  "request_id": "0a32fd9e-6f11-4d39-9a17-5c36f1b3f001",
  "source": "server_api",
  "intent": "resolve_email_recipient",
  "payload": {
    "recipient_query": "Сергей Засулин",
    "mode": "quick"
  }
}
```

Обязательные поля:
- `recipient_query`

Опциональные поля:
- `mode`: `quick | full`

### 2. send_email

Используется, когда сервер уже знает текст и тему письма, а прототип должен:
- найти получателя;
- создать draft;
- при разрешении политики отправить.

```json
{
  "request_id": "9f84a7f9-d6ce-4aa4-b56f-53a9b9a6e101",
  "source": "server_api",
  "intent": "send_email",
  "payload": {
    "idempotency_key": "send-email-unique-key",
    "recipient_query": "Сергей Засулин",
    "subject": "Привет",
    "body": "Привет, как у тебя дела?",
    "mode": "quick",
    "account": {
      "selection": "mail_app_default",
      "name": null
    },
    "confirmation_required": true
  }
}
```

Обязательные поля:
- `idempotency_key`
- `recipient_query`
- `subject`
- `body`

Опциональные поля:
- `mode`: `quick | full`
- `account.selection`: сейчас поддержан `mail_app_default`
- `account.name`: зарезервировано под явный account selection
- `confirmation_required`: `true | false`

Server rule:
- если `confirmation_required=true`, сервер должен использовать результат `draft_created` и только потом вызывать `send_draft`;
- если `confirmation_required=false`, допустим auto-send только после `resolved`.

### 3. send_draft

Используется только для уже созданного draft.

```json
{
  "request_id": "0b1cb9a1-c309-4d82-8ad8-3d736b42f201",
  "source": "server_api",
  "intent": "send_draft",
  "payload": {
    "idempotency_key": "send-draft-unique-key",
    "draft_id": "10"
  }
}
```

Обязательные поля:
- `idempotency_key`
- `draft_id`

### 4. read_latest_unread

```json
{
  "request_id": "5b95d779-a224-4c1b-b290-7d3fd168e301",
  "source": "server_api",
  "intent": "read_latest_unread",
  "payload": {
    "account": "Google",
    "limit": 3,
    "scan_limit": 10
  }
}
```

Обязательные поля:
- `account`

Опциональные поля:
- `limit` default: `1`
- `scan_limit` default: `10`

### 5. read_latest_from

```json
{
  "request_id": "f4f6dd65-2afd-4501-bf3f-d8fa2a091401",
  "source": "server_api",
  "intent": "read_latest_from",
  "payload": {
    "account": "Google",
    "recipient_query": "Сергей Засулин",
    "mode": "quick",
    "limit": 1,
    "scan_limit": 10
  }
}
```

Обязательные поля:
- `account`
- `recipient_query`

Опциональные поля:
- `mode`: `quick | full`
- `limit`
- `scan_limit`

### 6. refresh_recipient_index

```json
{
  "request_id": "52f269e3-c2d6-4b64-8cda-a8c7d5a52d01",
  "source": "server_api",
  "intent": "refresh_recipient_index",
  "payload": {
    "mode": "quick",
    "per_account_limit": 10
  }
}
```

### 7. recipient_index_status

```json
{
  "request_id": "f49d9419-1499-49a7-9d0f-1740f74ec801",
  "source": "server_api",
  "intent": "recipient_index_status",
  "payload": {}
}
```

### 8. preflight_health

Используется как единая readiness-check команда до реальных mail actions.

```json
{
  "request_id": "0f59033e-25c8-4b6d-8d36-182d8f98d001",
  "source": "server_api",
  "intent": "preflight_health",
  "payload": {}
}
```

## Canonical Response Envelope

Все ответы должны возвращаться строго в одном envelope:

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
- `success=true` только для terminal-success;
- `success=false` для `ambiguous`, `not_found`, `error`;
- `data` всегда содержит domain payload;
- `error` всегда structured object или `null`.

Минимальный стабильный набор `status` для интеграции:
- `ok`
- `resolved`
- `ambiguous`
- `not_found`
- `draft_created`
- `sent`
- `error`
- `not_ready`

## Response Payload Requirements

### resolve_email_recipient

`data` должно содержать:
- `intent`
- `recipientQuery`
- `resolutionStatus`
- `resolvedRecipient`
- `matches`
- `message`
- `index`

Статусы:
- `resolved`
- `ambiguous`
- `not_found`

### send_email

`data` должно содержать:
- `intent`
- `recipientQuery`
- `resolutionStatus`
- `resolvedRecipient`
- `account`
- `subject`
- `body`
- `draftId` после создания draft

Статусы:
- `draft_created`
- `ambiguous`
- `not_found`
- `error`

### send_draft

`data` должно содержать:
- `intent`
- `draftId`

Статусы:
- `sent`
- `error`

### preflight_health

`data` должно содержать:
- `intent`
- `mailAppAvailable`
- `automationPermission`
- `mailboxesAccessible`
- `recipientIndexAvailable`
- `ready`

Статусы:
- `ok`
- `not_ready`

### read_latest_unread

`data` должно содержать:
- `intent`
- `account`
- `limit`
- `scanLimit`
- `count`
- `messages`

### read_latest_from

`data` должно содержать:
- `intent`
- `recipientQuery`
- `resolutionStatus`
- `resolvedRecipient`
- `account`
- `limit`
- `scanLimit`
- `count`
- `messages`

## Message Object Contract

Каждый элемент в `messages[]` должен содержать:
- `subject`
- `sender`
- `messageId`
- `content`

Минимальный объект:

```json
{
  "subject": "Hello",
  "sender": "Sergiy Zasorin <seregawpn@gmail.com>",
  "messageId": "7F786C1B-C613-4279-8D69-F24FD715B1A3@gmail.com",
  "content": "Привет"
}
```

## Decision Table

### Recipient resolution

- `resolved`
  - можно создавать draft;
  - можно читать по sender.

- `ambiguous`
  - сервер не должен продолжать send/read-from;
  - сервер должен показать `matches[]` и запросить уточнение.

- `not_found`
  - сервер не должен продолжать send/read-from;
  - сервер должен вернуть сообщение: `Контакт не найден. Повторите имя или укажите email.`

### Send workflow

- `draft_created`
  - safe state;
  - сервер может показать preview/confirm;
  - отправка только отдельным `send_draft`.

- `sent`
  - terminal-success;
  - повторная отправка этого же `draftId` сервером запрещена.

### Preflight workflow

- `ok`
  - сервер может выполнять mail action

- `not_ready`
  - сервер не должен запускать `send_email`, `send_draft`, `read_latest_unread`, `read_latest_from`
  - сервер должен вернуть diagnostic reason

## Tested Scenarios

Ниже только сценарии, подтвержденные реальными вызовами.

### 1. Recipient index status

Проверено:
- `recipient_index_status`

Результат:
- `success=true`
- `status=ok`
- `data.exists=true`

### 2. Recipient resolved

Проверено:
- `find-recipient --mode quick --query 'seregawpn@gmail.com'`

Результат:
- `success=true`
- `status=resolved`
- `resolvedRecipient.email=seregawpn@gmail.com`

### 3. Recipient ambiguous

Проверено:
- `find-recipient --mode quick --query 'Sergiy Zasorin'`

Результат:
- `success=false`
- `status=ambiguous`
- `matches` содержит 2 email

### 4. Recipient not found

Проверено:
- `find-recipient --mode quick --query 'John Smith'`

Результат:
- `success=false`
- `status=not_found`

### 5. Read latest unread

Проверено:
- `read-latest-unread --account Google --limit 1 --scan-limit 5`

Результат:
- `success=true`
- `status=ok`
- `messages[0]` содержит `subject/sender/messageId/content`

### 6. Read latest from sender

Проверено:
- `read-latest-from --mode quick --account Google --query 'seregawpn@gmail.com' --limit 1 --scan-limit 10`

Результат:
- `success=true`
- `status=ok`
- sender корректно resolved
- последнее письмо прочитано

### 7. Create draft

Проверено:
- `create-draft --to seregawpn@gmail.com --subject 'Req smoke' --body 'Prototype requirement smoke test.'`

Результат:
- `success=true`
- `status=draft_created`
- возвращен `draftId=10`

### 8. Send draft

Проверено:
- `send-draft --draft-id 10`

Результат:
- `success=true`
- `status=sent`

## Failure-Safe Rules

Чтобы систему было проще чинить, использовать только эти правила:

1. Любой send request должен быть идемпотентным.
2. Любой side-effect path должен иметь один явный статус результата.
3. Любая неготовность runtime должна возвращаться через `preflight_health`.
4. Любая неоднозначность recipient должна завершать flow до send/read.
5. Любая ошибка должна приходить в одном envelope, а не через исключения transport-слоя.

## Minimal Error Taxonomy

`error.code` должен быть только из этого списка:

- `invalid_request`
- `ambiguous`
- `not_found`
- `not_ready`
- `mail_unavailable`
- `mail_permission_denied`
- `send_failed`
- `read_failed`
- `timeout`
- `internal_error`

## Server Integration Rules

Сервер должен делать только это:

1. Распознать user intent.
2. Заполнить канонический request envelope.
3. Передать в прототип:
   - `recipient_query`
   - `subject`
   - `body`
   - `account`
   - `limit/scan_limit`
   - `confirmation_required`
4. Не делать локальный email lookup параллельно с прототипом.
5. Не отправлять без `draftId`.
6. Не продолжать flow при `ambiguous/not_found`.
7. Перед первым mail action вызывать `preflight_health`.
8. Для `send_email` и `send_draft` всегда передавать `idempotency_key`.
9. Не строить callback path до тех пор, пока sync contract полностью не стабилизирован.

## Minimal Server Payload Examples

### Пример: написать сообщение Сергею Засулину

```json
{
  "request_id": "2ec4fcfa-88e4-45fd-b822-62085ec2b901",
  "source": "server_api",
  "intent": "send_email",
  "payload": {
    "idempotency_key": "send-email-2026-03-14-0001",
    "recipient_query": "Сергей Засулин",
    "subject": "Привет",
    "body": "Привет, как у тебя дела?",
    "mode": "quick",
    "account": {
      "selection": "mail_app_default",
      "name": null
    },
    "confirmation_required": true
  }
}
```

### Пример: прочитать последние непрочитанные

```json
{
  "request_id": "5f22d2bb-7efe-4a95-b17a-124ef7612301",
  "source": "server_api",
  "intent": "read_latest_unread",
  "payload": {
    "account": "Google",
    "limit": 3,
    "scan_limit": 10
  }
}
```

### Пример: preflight перед действием

```json
{
  "request_id": "6ffea82e-c588-4dc0-bf6e-f69001e59801",
  "source": "server_api",
  "intent": "preflight_health",
  "payload": {}
}
```

### Пример: прочитать последнее письмо от Сергея Засулина

```json
{
  "request_id": "4d4fca2f-0cf2-4112-aa4d-b5fdb6d2c401",
  "source": "server_api",
  "intent": "read_latest_from",
  "payload": {
    "account": "Google",
    "recipient_query": "Сергий Засулин",
    "mode": "quick",
    "limit": 1,
    "scan_limit": 10
  }
}
```

## Known Constraints

- Текущий owner отправки: `Mail.app`.
- Текущий owner чтения: `Mail.app -> account mailbox`.
- Текущий account selection для отправки: `mail_app_default`.
- `mode=quick` рекомендован как default для интерактивного UX.
- `full` нужен только для более глубокого recipient scan.

## Recommended Defaults

- `mode=quick`
- `confirmation_required=true`
- `account.selection=mail_app_default`
- `read_latest_unread.limit=3`
- `read_latest_from.limit=1`
- `scan_limit=10`
- `sync transport only`
- `preflight before first action`

## Rejected Patterns

Не использовать:
- raw user text как единственный вход в mail bridge;
- server-side recipient guessing поверх отдельного lookup;
- direct send без отдельного `draftId`;
- смешивание `Contacts` и mail-history как двух равноправных источников получателя;
- обязательные callback/webhook flows на первом этапе;
- retry send без `idempotency_key`.
