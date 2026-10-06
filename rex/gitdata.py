import os
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Set

def run_git(cmd: List[str], cwd: Path) -> str:
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["LC_ALL"] = "C"
    
    full_cmd = ["git", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", "--no-pager"] + cmd
    res = subprocess.run(full_cmd, cwd=cwd, env=env, check=True, capture_output=True, text=True)
    return res.stdout.strip()

def get_merge_base(repo: Path, branch: str, base_branch: str = "main") -> str:
    return run_git(["merge-base", base_branch, branch], repo)

def get_diff_numstat(repo: Path, merge_base: str, head: str) -> List[Tuple[int, int, str]]:
    out = run_git(["diff", "--numstat", "--no-renames", f"{merge_base}..{head}"], repo)
    res = []
    for line in out.splitlines():
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) == 3:
            add, rem, path = parts
            a = 0 if add == '-' else int(add)
            r = 0 if rem == '-' else int(rem)
            res.append((a, r, path))
    return res

def get_added_lines_and_diff_text(repo: Path, merge_base: str, head: str) -> Tuple[List[str], str]:
    diff = run_git(["diff", "--no-renames", f"{merge_base}..{head}"], repo)
    added = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    return added, diff

def get_commits_touching_files(repo: Path, merge_base: str, paths: List[str]) -> List[Dict[str, str]]:
    if not paths:
        return []
    # Using %H and %s exactly. No author info.
    out = run_git(["log", "--format=%H%x00%s", "--no-renames", merge_base, "--"] + paths, repo)
    res = []
    for line in out.splitlines():
        if not line:
            continue
        parts = line.split('\x00', 1)
        if len(parts) == 2:
            res.append({"sha": parts[0], "subject": parts[1]})
    return res

def get_all_commits_in_history(repo: Path, merge_base: str) -> List[str]:
    out = run_git(["log", "--format=%H", merge_base], repo)
    return [l for l in out.splitlines() if l]

def get_commit_stats(repo: Path, sha: str) -> List[Tuple[int, int, str]]:
    out = run_git(["show", "--numstat", "--no-renames", "--format=", sha], repo)
    res = []
    for line in out.splitlines():
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) == 3:
            add, rem, path = parts
            a = 0 if add == '-' else int(add)
            r = 0 if rem == '-' else int(rem)
            res.append((a, r, path))
    return res
