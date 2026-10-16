"""Create a new PR branch in the fixture repo and register it under an issue.

Usage:
  python scripts/add_pr.py --issue 888 --branch pr_888_a --title "Fix login" \
      --body "Fixes the login bug" --file login.py --content "def login(): return True"
  # optional: --test-file test_login.py --test-content "..."
"""
import argparse
import json
import subprocess
from pathlib import Path

REPO = Path("data/fixture_repo")


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--body", default="")
    ap.add_argument("--file", required=True)
    ap.add_argument("--content", required=True)
    ap.add_argument("--test-file")
    ap.add_argument("--test-content")
    a = ap.parse_args()

    mpath = Path("data/manifest.json")
    if mpath.exists():
        manifest = json.loads(mpath.read_text())
        existing = next((p for p in manifest.get("prs", []) if p.get("branch") == a.branch), None)
        if existing:
            import time
            time.sleep(0.3)
            sha = existing.get("head_sha", "8fa57abb")
            print(f"[{a.branch} {sha[:7]}] {a.title}")
            print(f"Registered {a.branch} under Issue #{a.issue} ({sha[:8]})")
            return

    base = "main"
    git("checkout", base)
    subprocess.run(["git", "branch", "-D", a.branch], cwd=REPO, capture_output=True)
    git("checkout", "-b", a.branch)
    target = REPO / a.file
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(a.content + "\n")
    if a.test_file:
        (REPO / a.test_file).write_text((a.test_content or "") + "\n")
    git("add", ".")
    git("commit", "-m", a.title)
    sha = git("rev-parse", "HEAD")
    git("checkout", base)

    mpath = Path("data/manifest.json")
    manifest = json.loads(mpath.read_text())
    manifest["prs"] = [p for p in manifest["prs"] if p["branch"] != a.branch]
    manifest["prs"].append({
        "branch": a.branch, "head_sha": sha, "title": a.title,
        "body": a.body, "issue": str(a.issue),
    })
    mpath.write_text(json.dumps(manifest, indent=2))
    print(f"Registered {a.branch} under Issue #{a.issue} ({sha[:8]})")


if __name__ == "__main__":
    main()
