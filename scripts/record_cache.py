import argparse
import json
from pathlib import Path
from rex.models import PRMetadata
from rex.risk import calculate_risk
from rex.router import route_review, record_ranking
from rex.cache import get_cache_path
from rex.config import PROMPT_VERSION

def clear_cache_file(task, subject_id, variant):
    p = get_cache_path(task, subject_id, variant, PROMPT_VERSION)
    if p.exists():
        p.unlink()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--only-missing", action="store_true")
    args = parser.parse_args()
    
    if args.force and args.only_missing:
        print("Cannot specify both --force and --only-missing")
        return
        
    if not args.force:
        args.only_missing = True
        
    repo = Path("data/fixture_repo")
    with open("data/manifest.json") as f:
        manifest = json.load(f)
        
    prs = [PRMetadata(**p) for p in manifest["prs"]]
    issue_42_prs = [p for p in prs if p.issue == "42"]
    
    for pr in prs:
        risk = calculate_risk(repo, pr.branch, pr.title, pr.body)
        
        if args.force:
            clear_cache_file("summary" if risk.tier == "LOW" else "deep", f"pr_{pr.branch}", "default")
            clear_cache_file("counterfactual_deep", f"pr_{pr.branch}", "default")
            
        print(f"Recording {pr.branch}...")
        if risk.tier == "LOW":
            res1 = route_review(repo, pr, risk, counterfactual=False)
            print(res1)
            res2 = route_review(repo, pr, risk, counterfactual=True)
            print(res2)
        else:
            res = route_review(repo, pr, risk, counterfactual=False)
            print(res)
            
    issues_map = {}
    for p in prs:
        if p.issue:
            issues_map.setdefault(p.issue, []).append(p)
            
    for issue_id, issue_prs in issues_map.items():
        if len(issue_prs) != 2:
            continue
        cand_a, cand_b = issue_prs
        if args.force:
            clear_cache_file("ranking", f"issue_{issue_id}", "AB")
            clear_cache_file("ranking", f"issue_{issue_id}", "BA")
            
        print(f"Recording ranking for Issue {issue_id}...")
        print(record_ranking(repo, issue_id, cand_a, cand_b, "AB"))
        print(record_ranking(repo, issue_id, cand_b, cand_a, "BA"))
        
if __name__ == "__main__":
    main()
