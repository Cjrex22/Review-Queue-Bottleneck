"""
Create a full demo issue with 6 competing PRs (3 good, 3 bad) in one command.

Usage:
    PYTHONPATH=. python3 scripts/demo_issue.py --issue 600

After running, record cache and view in dashboard:
    OPENAI_API_KEY="..." REX_MODEL="llama-3.3-70b-versatile" LLM_PROVIDER="auto" PYTHONPATH=. python3 scripts/record_cache.py --force
"""
import argparse
import json
import subprocess
from pathlib import Path

REPO = Path("data/fixture_repo")


def git(*args, check=True):
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=check
    ).stdout.strip()


def make_branch(branch, title, body, files, issue):
    """Create a branch, write files, commit, return sha."""
    git("checkout", "main")
    subprocess.run(["git", "branch", "-D", branch], cwd=REPO, capture_output=True)
    git("checkout", "-b", branch)
    for path, content in files.items():
        target = REPO / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    git("add", ".")
    git("commit", "-m", title)
    sha = git("rev-parse", "HEAD")
    git("checkout", "main")
    return {"branch": branch, "head_sha": sha, "title": title, "body": body, "issue": str(issue)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", default="600")
    a = ap.parse_args()
    issue = a.issue

    prs_to_add = []

    # ── PR 1: GOOD – clean logic + full tests (LOW risk, highest rank) ──────
    prs_to_add.append(make_branch(
        f"pr_{issue}_auth_clean",
        "feat: add secure auth token validator with tests",
        f"Fixes #{issue}. Full implementation with unit tests and docstrings.",
        {
            f"auth/validator_{issue}.py": (
                "def validate_token(token: str) -> bool:\n"
                "    \"\"\"Return True if token is non-empty and at least 12 chars.\"\"\"\n"
                "    return bool(token) and len(token) >= 12\n"
            ),
            f"tests/test_validator_{issue}.py": (
                f"from auth.validator_{issue} import validate_token\n\n"
                "def test_valid(): assert validate_token('supersecret99') is True\n"
                "def test_empty(): assert validate_token('') is False\n"
                "def test_short(): assert validate_token('abc') is False\n"
            ),
        },
        issue,
    ))

    # ── PR 2: GOOD – payment module with tests (FORCED REVIEW, good rank) ───
    prs_to_add.append(make_branch(
        f"pr_{issue}_payment_clean",
        "feat: add payment amount validator with tests",
        f"Fixes #{issue}. Validates payment amounts with edge-case tests.",
        {
            f"payments/validate_{issue}.py": (
                "def validate_amount(amount: float) -> bool:\n"
                "    \"\"\"Return True if amount is positive and <= 1_000_000.\"\"\"\n"
                "    return 0 < amount <= 1_000_000\n"
            ),
            f"tests/test_payment_{issue}.py": (
                f"from payments.validate_{issue} import validate_amount\n\n"
                "def test_ok(): assert validate_amount(99.99)\n"
                "def test_zero(): assert not validate_amount(0)\n"
                "def test_over(): assert not validate_amount(2_000_000)\n"
            ),
        },
        issue,
    ))

    # ── PR 3: GOOD – large refactor, HIGH risk score but well structured ────
    prs_to_add.append(make_branch(
        f"pr_{issue}_refactor_clean",
        "refactor: restructure reporting module across 4 files",
        f"Fixes #{issue}. Clean refactor with proper separation of concerns.",
        {
            f"services/reporting/models_{issue}.py": "class Report:\n    def __init__(self, data): self.data = data\n",
            f"services/reporting/writers_{issue}.py": "def write_csv(report, path):\n    with open(path, 'w') as f: f.write(str(report.data))\n",
            f"services/reporting/readers_{issue}.py": "def read_csv(path):\n    with open(path) as f: return f.read()\n",
            f"tests/test_reporting_{issue}.py": (
                f"from services.reporting.models_{issue} import Report\n\n"
                "def test_init(): assert Report({'a':1}).data == {'a':1}\n"
            ),
        },
        issue,
    ))

    # ── PR 4: BAD – hardcoded secret (FORCED REVIEW, security override) ─────
    prs_to_add.append(make_branch(
        f"pr_{issue}_secret_leak",
        "fix: add api connection",
        f"Fixes #{issue}. Adds API key for integration.",
        {
            f"config/api_{issue}.py": (
                "# API credentials\n"
                "API_KEY = 'AKIA1234567890ABCDEF'\n"
                "def connect(): return API_KEY\n"
            ),
        },
        issue,
    ))

    # ── PR 5: BAD – spaghetti code, no tests (HIGH risk, low rank) ──────────
    prs_to_add.append(make_branch(
        f"pr_{issue}_spaghetti",
        "fix: rushed auth hack, no tests",
        f"Fixes #{issue}. Quick hack to unblock the team.",
        {
            f"auth/hack_{issue}.py": (
                "def do_auth(u, p, t, x, y, z, a=None, b=None):\n"
                + "    print('trying auth')\n" * 15
                + "    return True  # TODO: implement properly\n"
            ),
        },
        issue,
    ))

    # ── PR 6: BAD – bypasses validation, prints credentials (HIGH risk) ─────
    prs_to_add.append(make_branch(
        f"pr_{issue}_bypass",
        "fix: skip token check for now",
        f"Fixes #{issue}. Temporarily bypass for demo.",
        {
            f"auth/bypass_{issue}.py": (
                "def validate_token(token):\n"
                "    print(f'token={token}')  # debug\n"
                "    return True  # always pass\n"
            ),
        },
        issue,
    ))

    # ── Update manifest ──────────────────────────────────────────────────────
    mpath = Path("data/manifest.json")
    manifest = json.loads(mpath.read_text())
    # Remove old branches for this issue
    manifest["prs"] = [
        p for p in manifest["prs"]
        if not p["branch"].startswith(f"pr_{issue}_")
    ]
    manifest["prs"].extend(prs_to_add)
    mpath.write_text(json.dumps(manifest, indent=2))

    print(f"\n✅ Created 6 PRs for Issue #{issue}:")
    for pr in prs_to_add:
        print(f"   {pr['branch']:<35} sha={pr['head_sha'][:8]}")
    print(f"\n▶ Now run:\n")
    print(
        f'   OPENAI_API_KEY="<your-groq-api-key>" '
        f'REX_MODEL="llama-3.3-70b-versatile" LLM_PROVIDER="auto" '
        f'PYTHONPATH=. python3 scripts/record_cache.py --force'
    )
    print(f"\n   Then refresh the dashboard ↗  and open Issue #{issue} in PR Ranking.")


if __name__ == "__main__":
    main()
