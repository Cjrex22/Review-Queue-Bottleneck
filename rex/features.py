import math
import re
from pathlib import Path
from typing import List, Tuple, Dict, Set
from .gitdata import get_merge_base, get_diff_numstat, get_commits_touching_files, get_all_commits_in_history, get_commit_stats
from .config import CAP_FLOORS

def calculate_entropy(stats: List[Tuple[int, int, str]], cap_files: int) -> float:
    """
    Computes Hassan-style change entropy:
    p_i = (added_i + deleted_i) / lines over touched files with lines > 0;
    H = -Σ p_i·log2(p_i);
    entropy = clamp(H / log2(CAP_FILES), 0, 1).
    If files <= 1 or lines == 0, entropy = 0.
    """
    total_lines = sum(a + r for a, r, _ in stats)
    files_with_lines = sum(1 for a, r, _ in stats if a + r > 0)
    
    if files_with_lines <= 1 or total_lines == 0:
        return 0.0
        
    h = 0.0
    for a, r, _ in stats:
        lines = a + r
        if lines > 0:
            p = lines / total_lines
            h -= p * math.log2(p)
            
    val = h / math.log2(cap_files)
    return max(0.0, min(val, 1.0))

def get_unique_dirs(paths: List[str]) -> int:
    dirs = set()
    for p in paths:
        parent = str(Path(p).parent)
        if parent == ".":
            dirs.add("")
        else:
            dirs.add(parent)
    return len(dirs)

def compute_caps(repo: Path, merge_base: str) -> Dict[str, int]:
    commits = get_all_commits_in_history(repo, merge_base)
    file_counts = []
    dir_counts = []
    line_counts = []
    
    for sha in commits:
        stats = get_commit_stats(repo, sha)
        f_count = len(stats)
        paths = [p for _, _, p in stats]
        d_count = get_unique_dirs(paths)
        l_count = sum(a + r for a, r, _ in stats)
        
        file_counts.append(f_count)
        dir_counts.append(d_count)
        line_counts.append(l_count)
        
    file_counts.sort()
    dir_counts.sort()
    line_counts.sort()
    
    def p95(arr):
        if not arr: return 0
        idx = int(math.ceil(0.95 * len(arr))) - 1
        return arr[max(0, min(idx, len(arr)-1))]
        
    p95_f = p95(file_counts)
    p95_d = p95(dir_counts)
    p95_l = p95(line_counts)
    
    return {
        "files": max(p95_f, CAP_FLOORS["files"]),
        "dirs": max(p95_d, CAP_FLOORS["dirs"]),
        "lines": max(p95_l, CAP_FLOORS["lines"])
    }

def normalize_features(files: int, dirs: int, lines: int, entropy: float, defect_density: float, caps: Dict[str, int]) -> Dict[str, float]:
    cap_f = caps["files"]
    cap_d = caps["dirs"]
    cap_l = caps["lines"]
    
    n_files = min(math.log1p(max(files - 1, 0)) / math.log1p(cap_f - 1), 1.0) if cap_f > 1 else 1.0
    n_dirs = min(math.log1p(max(dirs - 1, 0)) / math.log1p(cap_d - 1), 1.0) if cap_d > 1 else 1.0
    
    n_lines = min(math.log1p(lines) / math.log1p(cap_l), 1.0) if cap_l > 0 else 1.0
    
    return {
        "files_touched": n_files,
        "dirs_touched": n_dirs,
        "lines": n_lines,
        "entropy": max(0.0, min(entropy, 1.0)),
        "prior_defect_density": max(0.0, min(defect_density, 1.0))
    }

def compute_defect_density(commits: List[Dict[str, str]]) -> float:
    if not commits:
        return 0.0
    
    pattern = re.compile(r"(?i)\b(fix(es|ed)?|bug|hotfix|defect|regression)\b")
    fix_commits = sum(1 for c in commits if pattern.search(c["subject"]))
    density = fix_commits / len(commits)
    
    return min(density, 0.5) / 0.5

def extract_features(repo: Path, branch: str) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, int], List[str]]:
    merge_base = get_merge_base(repo, branch)
    stats = get_diff_numstat(repo, merge_base, branch)
    
    files = len(stats)
    paths = [p for _, _, p in stats]
    dirs = get_unique_dirs(paths)
    lines = sum(a + r for a, r, _ in stats)
    
    caps = compute_caps(repo, merge_base)
    entropy = calculate_entropy(stats, caps["files"])
    
    history_commits = get_commits_touching_files(repo, merge_base, paths)
    defect_density = compute_defect_density(history_commits)
    
    raw = {
        "files": files,
        "dirs": dirs,
        "lines": lines,
        "entropy": entropy,
        "prior_defect_density": defect_density
    }
    
    norm = normalize_features(files, dirs, lines, entropy, defect_density, caps)
    
    return raw, norm, caps, paths
