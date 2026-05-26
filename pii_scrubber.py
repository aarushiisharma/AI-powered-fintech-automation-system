"""
PII Scrubber — Regex-based detection & masking engine.
Detects: credit cards (Luhn-validated), emails, phone numbers, SSNs.
Called explicitly via /pii/scrub endpoint — NOT as middleware.
"""

import re
from typing import NamedTuple


class PIIEntity(NamedTuple):
    entity_type: str
    original: str
    masked: str
    start: int
    end: int


# --- Luhn Algorithm for credit card validation ---
def _luhn_check(number: str) -> bool:
    """Validate a credit card number using the Luhn algorithm."""
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse = digits[::-1]
    for i, d in enumerate(reverse):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


# --- Regex patterns ---
PATTERNS = {
    "CREDIT_CARD": re.compile(
        r'\b(?:\d{4}[-\s]?){3}\d{1,4}\b'
    ),
    "EMAIL": re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    ),
    "PHONE": re.compile(
        r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b'
    ),
    "SSN": re.compile(
        r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'
    ),
}


def _mask_credit_card(card: str) -> str:
    """Mask all but last 4 digits: ****-****-****-1234"""
    digits = re.sub(r'\D', '', card)
    return f"****-****-****-{digits[-4:]}"


def _mask_email(email: str) -> str:
    """Mask email: a***e@***.com"""
    local, domain = email.split("@")
    ext = domain.split(".")[-1]
    masked_local = f"{local[0]}***{local[-1]}" if len(local) > 1 else f"{local[0]}***"
    return f"{masked_local}@***.{ext}"


def _mask_phone(phone: str) -> str:
    """Mask phone: ***-***-1234"""
    digits = re.sub(r'\D', '', phone)
    return f"***-***-{digits[-4:]}"


def _mask_ssn(ssn: str) -> str:
    """Mask SSN: ***-**-1234"""
    digits = re.sub(r'\D', '', ssn)
    return f"***-**-{digits[-4:]}"


MASKERS = {
    "CREDIT_CARD": _mask_credit_card,
    "EMAIL": _mask_email,
    "PHONE": _mask_phone,
    "SSN": _mask_ssn,
}


def scrub(text: str) -> tuple[str, list[dict]]:
    """
    Detect and mask PII in the given text.
    
    Returns:
        (masked_text, list of detected entities with type/original/masked)
    """
    entities: list[PIIEntity] = []

    for entity_type, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            original = match.group()

            # Credit cards require Luhn validation to reduce false positives
            if entity_type == "CREDIT_CARD":
                digits_only = re.sub(r'\D', '', original)
                if not _luhn_check(digits_only):
                    continue

            # SSNs: skip if it looks like a phone number (too many digits)
            if entity_type == "SSN":
                digits_only = re.sub(r'\D', '', original)
                if len(digits_only) != 9:
                    continue
                # Skip area numbers 000, 666, 900-999
                area = int(digits_only[:3])
                if area == 0 or area == 666 or area >= 900:
                    continue

            masked = MASKERS[entity_type](original)
            entities.append(PIIEntity(
                entity_type=entity_type,
                original=original,
                masked=masked,
                start=match.start(),
                end=match.end(),
            ))

    # Remove overlapping entities — keep the longer match
    entities.sort(key=lambda e: (e.start, -(e.end - e.start)))
    filtered: list[PIIEntity] = []
    for entity in entities:
        # Check if this entity overlaps with any already-accepted entity
        overlaps = False
        for accepted in filtered:
            if entity.start >= accepted.start and entity.end <= accepted.end:
                overlaps = True
                break
        if not overlaps:
            filtered.append(entity)
    entities = filtered

    # Sort by position (reverse) so replacements don't shift indices
    entities.sort(key=lambda e: e.start, reverse=True)

    masked_text = text
    for entity in entities:
        masked_text = masked_text[:entity.start] + entity.masked + masked_text[entity.end:]

    # Return entities in forward order for readability
    entities.reverse()

    return masked_text, [
        {
            "entity_type": e.entity_type,
            "original": e.original,
            "masked": e.masked,
        }
        for e in entities
    ]
