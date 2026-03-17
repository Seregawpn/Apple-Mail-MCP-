from __future__ import annotations

import re
from dataclasses import dataclass


ADDRESS_RE = re.compile(r"^\s*(?P<name>.*?)\s*<(?P<email>[^>]+)>\s*$")
NON_WORD_RE = re.compile(r"[^a-z0-9@._+-]+")
HEADER_RE = re.compile(r"^(From|To|Cc):\s*(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class RecipientCandidate:
    display_name: str
    email: str
    hit_count: int
    score: int


def parse_address(raw_value: str) -> tuple[str, str] | None:
    value = raw_value.strip()
    if not value:
        return None

    matched = ADDRESS_RE.match(value)
    if matched:
        name = matched.group("name").strip().strip('"')
        email = matched.group("email").strip().lower()
        return (name or email, email)

    if "@" in value:
        email = value.lower()
        local_part = email.split("@", 1)[0]
        return (local_part, email)

    return None


def split_addresses(raw_value: str) -> list[str]:
    if not raw_value:
        return []
    parts = [part.strip() for part in raw_value.split(",")]
    return [part for part in parts if part]


def extract_addresses_from_source(source: str) -> dict[str, list[str]]:
    source = (
        source.replace("\\n", "\n")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )
    result = {"from": [], "to": [], "cc": []}
    current_header: str | None = None
    current_value: list[str] = []

    def flush() -> None:
        nonlocal current_header, current_value
        if not current_header:
            return
        joined = " ".join(current_value).strip()
        if current_header in result and joined:
            result[current_header].extend(split_addresses(joined))
        current_header = None
        current_value = []

    for line in source.splitlines():
        if not line:
            flush()
            break
        if line.startswith((" ", "\t")) and current_header:
            current_value.append(line.strip())
            continue

        flush()
        matched = HEADER_RE.match(line)
        if not matched:
            continue
        current_header = matched.group(1).lower()
        current_value = [matched.group(2).strip()]

    flush()
    return result


def normalize_text(value: str) -> str:
    lowered = value.lower().strip()
    return " ".join(NON_WORD_RE.sub(" ", lowered).split())


def build_candidates(messages: list[dict]) -> list[dict]:
    aggregated: dict[str, dict] = {}
    for message in messages:
        raw_values = [message.get("sender", "")]
        raw_values.extend(message.get("toRecipients", []))
        raw_values.extend(message.get("ccRecipients", []))

        for raw_value in raw_values:
            parsed = parse_address(raw_value)
            if not parsed:
                continue
            display_name, email = parsed
            candidate = aggregated.setdefault(
                email,
                {
                    "display_name": display_name,
                    "email": email,
                    "hit_count": 0,
                },
            )
            candidate["hit_count"] += 1
            if len(display_name) > len(candidate["display_name"]):
                candidate["display_name"] = display_name
    return list(aggregated.values())


def resolve_candidates(messages: list[dict], query: str, max_results: int = 5) -> list[RecipientCandidate]:
    normalized_query = normalize_text(query)
    if not normalized_query:
        return []

    query_tokens = normalized_query.split()
    resolved: list[RecipientCandidate] = []
    for candidate in build_candidates(messages):
        display_name = normalize_text(candidate["display_name"])
        email = normalize_text(candidate["email"])
        local_part = normalize_text(candidate["email"].split("@", 1)[0])

        score = 0
        matched = False
        if normalized_query == display_name:
            score += 120
            matched = True
        if normalized_query == email or normalized_query == local_part:
            score += 120
            matched = True
        if normalized_query and normalized_query in display_name:
            score += 60
            matched = True
        if normalized_query and normalized_query in email:
            score += 50
            matched = True

        searchable = f"{display_name} {email} {local_part}".strip()
        if query_tokens and all(token in searchable for token in query_tokens):
            score += 80 + len(query_tokens) * 5
            matched = True

        if not matched:
            continue
        score += min(candidate["hit_count"], 20)

        resolved.append(
            RecipientCandidate(
                display_name=candidate["display_name"],
                email=candidate["email"],
                hit_count=candidate["hit_count"],
                score=score,
            )
        )

    resolved.sort(key=lambda item: (-item.score, -item.hit_count, item.display_name.lower(), item.email))
    return resolved[:max_results]
