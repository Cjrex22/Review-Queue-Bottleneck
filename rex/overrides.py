import re
from typing import List
from .config import SENSITIVE_CATEGORIES, SECRET_PATTERNS, INJECTION_PATTERNS

def check_overrides(added_lines: List[str], touched_files: List[str]) -> List[str]:
    reasons = set()
    
    # Sensitive Paths
    for path in touched_files:
        for cat, triggers in SENSITIVE_CATEGORIES.items():
            for t in triggers:
                if t in path:
                    reasons.add(f"SENSITIVE_PATH:{cat}")
                    break

    # Secret Patterns
    compiled_secrets = [re.compile(p) for p in SECRET_PATTERNS]
    for line in added_lines:
        for i, pat in enumerate(compiled_secrets):
            if pat.search(line):
                reasons.add(f"SECRET_CONTENT:rule_{i+1}")
                
    return sorted(list(reasons))

def detect_injection(text: str) -> bool:
    if not text:
        return False
    for pat in INJECTION_PATTERNS:
        if re.search(pat, text):
            return True
    return False
