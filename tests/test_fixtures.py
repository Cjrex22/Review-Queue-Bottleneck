import os
import json
import pytest
import subprocess
import tempfile
from pathlib import Path

from scripts.build_fixtures import build

def run_git(cmd, cwd, env_updates=None):
    env = os.environ.copy()
    if env_updates:
        for k, v in env_updates.items():
            env[k] = str(v)
    res = subprocess.run(["git"] + cmd, cwd=cwd, env=env, check=True, capture_output=True, text=True)
    return res.stdout.strip()

def test_fixtures_determinism():
    base_temp = Path(tempfile.gettempdir())
    repo1 = base_temp / "repo1"
    man1 = base_temp / "man1.json"
    repo2 = base_temp / "repo2"
    man2 = base_temp / "man2.json"
    
    build(str(repo1), str(man1))
    
    fake_home = base_temp / "fake_home"
    fake_home.mkdir(exist_ok=True)
    with open(fake_home / ".gitconfig", "w") as f:
        f.write("[user]\n\tname = Adversary\n\temail = adv@example.com\n")
    
    original_home = os.environ.get("HOME")
    try:
        os.environ["HOME"] = str(fake_home)
        build(str(repo2), str(man2))
    finally:
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            del os.environ["HOME"]
            
    with open(man1) as f:
        m1 = json.load(f)
        
    with open(man2) as f:
        m2 = json.load(f)
        
    assert m1["base_sha"] == m2["base_sha"]
    assert len(m1["prs"]) == len(m2["prs"])
    for p1, p2 in zip(m1["prs"], m2["prs"]):
        assert p1["branch"] == p2["branch"]
        assert p1["head_sha"] == p2["head_sha"]
        
    commit_count = int(run_git(["rev-list", "--count", "main"], repo1))
    assert commit_count >= 60
    
    branches = run_git(["branch", "--format=%(refname:short)"], repo1).split()
    expected = [
        "pr_typo_fix", "pr_injection_low", "pr_auth_change",
        "pr_issue42_a", "pr_issue42_b", "pr_large_refactor"
    ]
    for b in expected:
        assert b in branches

    # Also assert against data/manifest.json if it exists
    real_manifest_path = Path("data/manifest.json")
    if real_manifest_path.exists():
        with open(real_manifest_path) as f:
            real_m = json.load(f)
        assert real_m["base_sha"] == m1["base_sha"]
        for rm, m in zip(real_m["prs"], m1["prs"]):
            assert rm["branch"] == m["branch"]
            assert rm["head_sha"] == m["head_sha"]
