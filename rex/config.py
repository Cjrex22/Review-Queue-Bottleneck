import math

RISK_WEIGHTS = {
    "lines": 0.30,
    "files_touched": 0.25,
    "dirs_touched": 0.20,
    "entropy": 0.15,
    "prior_defect_density": 0.10
}

if not math.isclose(sum(RISK_WEIGHTS.values()), 1.0, rel_tol=1e-9):
    raise RuntimeError("RISK_WEIGHTS must sum to 1.00")

RANKING_WEIGHTS = {
    "test_delta_score": 0.25,
    "blast_radius_score": 0.25,
    "diff_efficiency_score": 0.10,
    "requirement_completeness": 0.20,
    "architectural_alignment": 0.20
}

if not math.isclose(sum(RANKING_WEIGHTS.values()), 1.0, rel_tol=1e-9):
    raise RuntimeError("RANKING_WEIGHTS must sum to 1.00")

RISK_THRESHOLD = 0.35
PROMPT_VERSION = "v1"

CAP_FLOORS = {
    "files": 8,
    "dirs": 4,
    "lines": 200
}

SENSITIVE_CATEGORIES = {
    "auth": ["auth", "oauth", "sso"],
    "payments": ["payments"],
    "crypto": ["crypto/", ".pem", ".key"],
    "secrets": [".env", "secrets/", "credentials"],
    "security": ["security"],
    "ci_cd": [".github/workflows/"]
}

SECRET_PATTERNS = [
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"
]

INJECTION_PATTERNS = [
    r"</untrusted_diff",
    r"(?i)ignore (all|any|previous|prior) instructions",
    r"(?i)mark (this )?(pr )?low",
    r"(?i)you are now",
    r"(?i)system prompt"
]
