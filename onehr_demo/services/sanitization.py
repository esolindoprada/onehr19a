
import re

_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_ -]?key|private[_ -]?key)\b\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._~+/=-]+)"),
]

def sanitize_text(value, limit=4000):
    text = str(value or "").replace("\\x00", "")
    for pattern in _PATTERNS:
        text = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]", text)
    if len(text) > limit:
        text = text[:max(0, limit - 18)] + "… [TRUNCATED]"
    return text

def safe_exception_summary(exc, limit=1200):
    return sanitize_text(f"{type(exc).__name__}: {exc}", limit=limit)

