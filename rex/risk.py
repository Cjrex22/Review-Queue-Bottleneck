from pathlib import Path
from .features import extract_features
from .gitdata import get_added_lines_and_diff_text, get_merge_base
from .overrides import check_overrides, detect_injection
from .config import RISK_WEIGHTS, RISK_THRESHOLD
from .models import RiskResult, RawFeatures, NormalizedFeatures, OverrideResults

def calculate_risk(repo: Path, branch: str, title: str = "", body: str = "") -> RiskResult:
    raw, norm, caps, paths = extract_features(repo, branch)
    
    score = (
        norm["lines"] * RISK_WEIGHTS["lines"] +
        norm["files_touched"] * RISK_WEIGHTS["files_touched"] +
        norm["dirs_touched"] * RISK_WEIGHTS["dirs_touched"] +
        norm["entropy"] * RISK_WEIGHTS["entropy"] +
        norm["prior_defect_density"] * RISK_WEIGHTS["prior_defect_density"]
    )
    score = round(max(0.0, min(score, 1.0)), 2)
    
    merge_base = get_merge_base(repo, branch)
    added_lines, diff = get_added_lines_and_diff_text(repo, merge_base, branch)
    
    reasons = check_overrides(added_lines, paths)
    
    inj_text = f"{diff}\n{title}\n{body}"
    injection = detect_injection(inj_text)
    
    if reasons:
        label = "FORCED REVIEW (override)"
        tier = "HIGH"
    elif score >= RISK_THRESHOLD:
        label = "HIGH RISK (math)"
        tier = "HIGH"
    else:
        label = "LOW RISK (math)"
        tier = "LOW"
        
    return RiskResult(
        raw_features=RawFeatures(**raw),
        normalized_features=NormalizedFeatures(**norm),
        risk_score=score,
        overrides=OverrideResults(reasons=reasons, injection_detected=injection),
        label=label,
        tier=tier
    )
