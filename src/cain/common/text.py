"""Small shared normalization utility, with no backend dependencies."""

import re
import unicodedata


def tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return set(re.findall(r"\w+", "".join(c for c in normalized if not unicodedata.combining(c))))
