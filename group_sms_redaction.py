"""Redact authentication secrets before showing SMS text in a group."""

import re

_REDACTED = '••••••'
_URL_RE = re.compile(r'(?i)\b(?:https?://|www\.)\S+')
_LABEL_RE = re.compile(
    r'(?i)(\b(?:otp|pin|passcode|password|token|verification[\s_-]*code|'
    r'security[\s_-]*code|one[\s-]*time[\s-]*(?:code|password)|kod|şifrə)'
    r'\s*(?::|=|is|-)\s*)([A-Za-z0-9][A-Za-z0-9._-]{2,})'
)
_NUMERIC_CODE_RE = re.compile(r'(?<!\d)(?:\d{3}[\s-]+\d{3}|\d{4,8})(?!\d)')


def redact_group_sms(message, otp_code=None):
    """Keep non-secret SMS text, suppress all likely one-time credentials/links.

    Heuristic masking errs toward hiding too much rather than leaking a login code.
    """
    if not message:
        return 'SMS mətni yoxdur'
    text = str(message)
    text = _URL_RE.sub('[keçid gizlədilib]', text)
    code = str(otp_code or '').strip()
    if len(code) >= 3 and code.upper() not in ('N/A', 'NONE'):
        text = re.sub(re.escape(code), _REDACTED, text, flags=re.IGNORECASE)
        if code.isdigit() and len(code) == 6:
            spaced = r'[\s-]*'.join(re.escape(x) for x in code)
            text = re.sub(spaced, _REDACTED, text)
    text = _LABEL_RE.sub(lambda m: m.group(1) + _REDACTED, text)
    text = _NUMERIC_CODE_RE.sub(_REDACTED, text)
    return text
