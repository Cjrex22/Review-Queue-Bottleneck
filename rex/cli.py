import argparse
import json
import sys
import subprocess
from pathlib import Path
from .risk import calculate_risk
from .models import PRMetadata

def score():
    repo = Path("data/fixture_repo")
    manifest_path = Path("data/manifest.json")
    if not manifest_path.exists():
        print("Manifest not found")
        return
        
    with open(manifest_path) as f:
        manifest = json.load(f)
        
    print(f"{'Branch':<20} | {'Score':<5} | {'Label':<25} | {'Overrides':<25} | {'Inj'}")
    print("-" * 85)
    for pr in manifest["prs"]:
        res = calculate_risk(repo, pr["branch"], pr["title"], pr["body"])
        reasons = ", ".join(res.overrides.reasons) if res.overrides.reasons else "-"
        inj = "Y" if res.overrides.injection_detected else "N"
        print(f"{pr['branch']:<20} | {res.risk_score:<5.2f} | {res.label:<25} | {reasons:<25} | {inj}")

def review(pr_id: str):
    from .router import route_review
    repo = Path("data/fixture_repo")
    manifest_path = Path("data/manifest.json")
    if not manifest_path.exists():
        print("Manifest not found")
        return
        
    with open(manifest_path) as f:
        manifest = json.load(f)
        
    prs = [PRMetadata(**p) for p in manifest["prs"] if p["branch"] == pr_id]
    if not prs:
        print(f"PR {pr_id} not found in manifest")
        return
        
    pr = prs[0]
    risk = calculate_risk(repo, pr.branch, pr.title, pr.body)
    res = route_review(repo, pr, risk, counterfactual=False)
    print(json.dumps(res, indent=2))

def rank(issue: str):
    from .ranking import rank_prs
    from .cache import check_cache
    from .config import PROMPT_VERSION
    
    repo = Path("data/fixture_repo")
    with open("data/manifest.json") as f:
        manifest = json.load(f)
        
    prs = [PRMetadata(**p) for p in manifest["prs"] if p.get("issue") == issue]
    if len(prs) != 2:
        print(f"Need exactly 2 PRs for issue {issue}")
        return
        
    shas = {prs[0].branch: prs[0].head_sha, prs[1].branch: prs[1].head_sha}
    
    cache_ab = check_cache("ranking", f"issue_{issue}", "AB", PROMPT_VERSION, expected_shas=shas)
    cache_ba = check_cache("ranking", f"issue_{issue}", "BA", PROMPT_VERSION, expected_shas=shas)
    
    if not cache_ab or not cache_ba or cache_ab == "CACHE_MISS_STALE" or cache_ba == "CACHE_MISS_STALE":
        print("Missing or stale cache for ranking. Run record_cache.py")
        return
        
    res = rank_prs(repo, issue, prs, cache_ab["response"], cache_ba["response"])
    print("recommended review order:")
    for p in res.recommended_review_order:
        print(f"Rank {p.rank}: {p.branch} (Score: {p.total_score:.2f}, Confidence: {p.confidence})")
        print(f"  Valid bugs: {len(p.bugs_found)} (Dropped: {p.dropped_findings_count})")
        print(f"  Why higher/lower: {p.why_ranked_higher_or_lower}")

def economics():
    from .tokens import calculate_savings, project_savings
    repo = Path("data/fixture_repo")
    with open("data/manifest.json") as f:
        manifest = json.load(f)
        
    prs = [PRMetadata(**p) for p in manifest["prs"]]
    res = calculate_savings(repo, prs)
    
    if res["savings"] is None:
        print("Missing cache. Run record_cache.py")
        return
        
    print(f"Recorded token reduction vs naive deep-review baseline (measured on the fixture set, n={res['n']})")
    print(f"Baseline tokens: {res['baseline_tokens']}")
    print(f"Actual tokens: {res['actual_tokens']}")
    print(f"RECORDED SAVINGS: {res['savings']*100:.1f}%")
    
    if res["savings"] < 0.7:
        print("Note: Recorded savings is below the 70% target.")
        
    print(f"Mean LOW tier tokens: {res['mean_low']:.0f}")
    print(f"Mean HIGH tier tokens: {res['mean_high']:.0f}")
    
    proj = project_savings(res["mean_low"], res["mean_high"], 0.70)
    print("\nPROJECTION: at 70% LOW share")
    print("Formula: 1.0 - ((mean_low * 0.7 + mean_high * 0.3) / mean_high)")
    print(f"Projected savings: {proj*100:.1f}%")

def demo():
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=True)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="REX Review Gate CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    
    sub.add_parser("score", help="Output risk scores and override flags")
    
    rev_p = sub.add_parser("review", help="Output single PR review")
    rev_p.add_argument("pr_id", help="The branch name of the PR")
    
    rank_p = sub.add_parser("rank", help="Output multi-PR ranking table")
    rank_p.add_argument("--issue", required=True, help="Issue ID to rank PRs for")
    
    sub.add_parser("economics", help="Output baseline vs REX token delta")
    sub.add_parser("roi", help="Alias for economics")
    sub.add_parser("savings", help="Alias for economics")
    
    sub.add_parser("demo", help="Launch the Streamlit UI dashboard")
    
    args = parser.parse_args()
    
    if args.cmd == "score":
        score()
    elif args.cmd == "review":
        review(args.pr_id)
    elif args.cmd == "rank":
        rank(args.issue)
    elif args.cmd in ("economics", "roi", "savings"):
        economics()
    elif args.cmd == "demo":
        demo()
