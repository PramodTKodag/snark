"""User-input privacy: redact structured PII before storing request input.

Dependency-light (stdlib re). Catches structured identifiers (email, credit
card, SSN-like, phone); it does NOT catch free-text names/addresses — bounded
retention limits that residual exposure. Microsoft Presidio (NER) is an
optional upgrade, not a dependency here.
"""

import re

from django.conf import settings

MAX_STORED_INPUT = 500

# Order matters: redact card/SSN before the broad phone pattern.
_PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    (re.compile(r"\b(?:\d[ -]?){13,16}\b"), "[card]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[ssn]"),
    (re.compile(r"\+?\d[\d\s().-]{7,}\d"), "[phone]"),
]


def redact(text: str) -> str:
    """Replace structured PII patterns with placeholders."""
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


def store_input(user_input: str) -> str:
    """Transform raw user input for storage per LOG_INPUT_MODE."""
    mode = getattr(settings, "LOG_INPUT_MODE", "redacted")
    if mode == "raw":
        return user_input
    if mode == "none" or not user_input:
        return ""
    return redact(user_input)[:MAX_STORED_INPUT]  # redacted (default + fallback)
