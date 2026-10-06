from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel
from .config import RANKING_WEIGHTS, PROMPT_VERSION
from .models import PRMetadata, BugFinding
from .features import compute_caps, extract_features
from .gitdata import get_merge_base, get_diff_added_lines_map
import json

class RankedPR(BaseModel):
    branch: str
    rank: int
    total_score: float
    test_delta_score: float
    blast_radius_score: float
    diff_efficiency_score: float
    requirement_completeness: float
    architectural_alignment: float
    time_complexity_notes: str
    memory_notes: str
    bugs_found: List[BugFinding]
    why_ranked_higher_or_lower: str
    confidence: str
    dropped_findings_count: int

class RankingResult(BaseModel):
    issue: str
    recommended_review_order: List[RankedPR]

def get_git_ranking_metrics(repo: Path, pr: PRMetadata) -> Dict[str, float]:
    import math
    mb = get_merge_base(repo, pr.branch)
    raw_features, _, caps, _ = extract_features(repo, pr.branch)
    
    diff_map = get_diff_added_lines_map(repo, mb, pr.branch)
    has_test = any("test" in f.lower() for f in diff_map.keys())
    test_delta_score = 1.0 if has_test else 0.0
    
    F = raw_features["files"]
    D = raw_features["dirs"]
    cap_F = caps["files"]
    cap_D = caps["dirs"]
    blast_val = math.log1p(max(F + D - 2, 0)) / math.log1p(cap_F + cap_D - 2) if (cap_F + cap_D - 2) > 0 else 0
    blast_radius_score = 1.0 - min(blast_val, 1.0)
    
    L = raw_features["lines"]
    cap_L = caps["lines"]
    diff_val = math.log1p(L) / math.log1p(cap_L) if cap_L > 0 else 0
    diff_efficiency_score = 1.0 - min(diff_val, 1.0)
    
    return {
        "test_delta_score": test_delta_score,
        "blast_radius_score": blast_radius_score,
        "diff_efficiency_score": diff_efficiency_score
    }

def validate_bugs(bugs: List[Dict], diff_map: Dict[str, set]) -> Tuple[List[Dict], int]:
    valid = []
    dropped = 0
    for bug in bugs:
        file = bug.get("file")
        line = bug.get("line")
        if file in diff_map and line in diff_map[file]:
            valid.append(bug)
        else:
            dropped += 1
    return valid, dropped

def rank_prs(repo: Path, issue: str, prs: List[PRMetadata], cache_ab: Dict, cache_ba: Dict) -> RankingResult:
    pr_metrics = [get_git_ranking_metrics(repo, pr) for pr in prs]
    diff_maps = [get_diff_added_lines_map(repo, get_merge_base(repo, p.branch), p.branch) for p in prs]
    
    c1_ab = cache_ab.get("Candidate 1", {})
    c2_ab = cache_ab.get("Candidate 2", {})
    c1_ba = cache_ba.get("Candidate 1", {})
    c2_ba = cache_ba.get("Candidate 2", {})
    
    req0_ab = c1_ab.get("requirement_completeness", 0)
    req0_ba = c2_ba.get("requirement_completeness", 0)
    req0 = (req0_ab + req0_ba) / 2.0 / 3.0
    
    arch0_ab = c1_ab.get("architectural_alignment", 0)
    arch0_ba = c2_ba.get("architectural_alignment", 0)
    arch0 = (arch0_ab + arch0_ba) / 2.0 / 3.0
    
    conf0 = "HIGH"
    if abs(req0_ab - req0_ba) > 1.0 or abs(arch0_ab - arch0_ba) > 1.0:
        conf0 = "LOW"
        
    req1_ab = c2_ab.get("requirement_completeness", 0)
    req1_ba = c1_ba.get("requirement_completeness", 0)
    req1 = (req1_ab + req1_ba) / 2.0 / 3.0
    
    arch1_ab = c2_ab.get("architectural_alignment", 0)
    arch1_ba = c1_ba.get("architectural_alignment", 0)
    arch1 = (arch1_ab + arch1_ba) / 2.0 / 3.0
    
    conf1 = "HIGH"
    if abs(req1_ab - req1_ba) > 1.0 or abs(arch1_ab - arch1_ba) > 1.0:
        conf1 = "LOW"
        
    bugs0_ab, drop0_ab = validate_bugs(c1_ab.get("bugs_found", []), diff_maps[0])
    bugs0_ba, drop0_ba = validate_bugs(c2_ba.get("bugs_found", []), diff_maps[0])
    drop0 = drop0_ab + drop0_ba
    
    bugs1_ab, drop1_ab = validate_bugs(c2_ab.get("bugs_found", []), diff_maps[1])
    bugs1_ba, drop1_ba = validate_bugs(c1_ba.get("bugs_found", []), diff_maps[1])
    drop1 = drop1_ab + drop1_ba
    
    def merge_bugs(b1, b2):
        res = []
        seen = set()
        for b in b1 + b2:
            key = (b.get("file"), b.get("line"), b.get("description"))
            if key not in seen:
                seen.add(key)
                res.append(b)
        return res
        
    bugs0 = merge_bugs(bugs0_ab, bugs0_ba)
    bugs1 = merge_bugs(bugs1_ab, bugs1_ba)
    
    def compute_total(metrics, req, arch):
        return (metrics["test_delta_score"] * RANKING_WEIGHTS["test_delta_score"] +
                metrics["blast_radius_score"] * RANKING_WEIGHTS["blast_radius_score"] +
                metrics["diff_efficiency_score"] * RANKING_WEIGHTS["diff_efficiency_score"] +
                req * RANKING_WEIGHTS["requirement_completeness"] +
                arch * RANKING_WEIGHTS["architectural_alignment"])
                
    score0 = compute_total(pr_metrics[0], req0, arch0)
    score1 = compute_total(pr_metrics[1], req1, arch1)
    
    def make_sort_key(score, metrics, pr):
        raw, _, _, _ = extract_features(repo, pr.branch)
        return (score, metrics["test_delta_score"], -raw["lines"], pr.head_sha)
        
    sk0 = make_sort_key(score0, pr_metrics[0], prs[0])
    sk1 = make_sort_key(score1, pr_metrics[1], prs[1])
    
    order = [0, 1] if sk0 > sk1 else [1, 0]
        
    ranked = []
    for rank, idx in enumerate(order, 1):
        pr = prs[idx]
        metrics = pr_metrics[idx]
        req = req0 if idx == 0 else req1
        arch = arch0 if idx == 0 else arch1
        conf = conf0 if idx == 0 else conf1
        bugs = bugs0 if idx == 0 else bugs1
        drop = drop0 if idx == 0 else drop1
        
        ab_cand = c1_ab if idx == 0 else c2_ab
        time_notes = ab_cand.get("time_complexity_notes", "")
        mem_notes = ab_cand.get("memory_notes", "")
        why = ab_cand.get("why_ranked_higher_or_lower", "")
        
        ranked.append(RankedPR(
            branch=pr.branch,
            rank=rank,
            total_score=round(score0 if idx == 0 else score1, 2),
            test_delta_score=round(metrics["test_delta_score"], 2),
            blast_radius_score=round(metrics["blast_radius_score"], 2),
            diff_efficiency_score=round(metrics["diff_efficiency_score"], 2),
            requirement_completeness=round(req, 2),
            architectural_alignment=round(arch, 2),
            time_complexity_notes=time_notes,
            memory_notes=mem_notes,
            bugs_found=[BugFinding(**b) for b in bugs],
            why_ranked_higher_or_lower=why,
            confidence=conf,
            dropped_findings_count=drop
        ))
        
    return RankingResult(issue=issue, recommended_review_order=ranked)
