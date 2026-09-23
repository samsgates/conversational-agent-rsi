from __future__ import annotations
import re
INJECTION_PATTERNS = [
    r"ignore (all|any|the) previous instructions",
    r"reveal (the )?(system|developer) prompt",
    r"print.*secret",
    r"exfiltrat",
]
SECRET_PATTERNS=[r"sk-[A-Za-z0-9]{20,}", r"AKIA[0-9A-Z]{16}"]

def inspect_text(text: str) -> dict[str, object]:
    matches=[p for p in INJECTION_PATTERNS if re.search(p,text,re.I)]
    secrets=[p for p in SECRET_PATTERNS if re.search(p,text)]
    return {"blocked":bool(matches or secrets),"injection_matches":matches,"secret_matches":secrets}
