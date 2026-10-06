import argparse
import json
from pathlib import Path
from .risk import calculate_risk

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("score")
    args = parser.parse_args()
    
    if args.cmd == "score":
        score()
