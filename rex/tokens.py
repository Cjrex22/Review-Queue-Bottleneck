import json
from pathlib import Path
from typing import Dict, Any, List
from .models import PRMetadata
from .cache import read_cache, get_cache_path
from .config import PROMPT_VERSION
from .risk import calculate_risk

def calculate_savings(repo: Path, prs: List[PRMetadata]) -> Dict[str, Any]:
    baseline = 0
    actual = 0
    low_actuals = []
    high_actuals = []
    
    missing = False
    for pr in prs:
        risk = calculate_risk(repo, pr.branch, pr.title, pr.body)
        if risk.tier == "LOW":
            cf_path = get_cache_path("counterfactual_deep", f"pr_{pr.branch}", "default", PROMPT_VERSION)
            sum_path = get_cache_path("summary", f"pr_{pr.branch}", "default", PROMPT_VERSION)
            cf_data = read_cache(cf_path)
            sum_data = read_cache(sum_path)
            if not cf_data or not sum_data:
                missing = True
                continue
            cf_tokens = cf_data.get("usage", {}).get("total_tokens", 0)
            act_tokens = sum_data.get("usage", {}).get("total_tokens", 0)
            baseline += cf_tokens
            actual += act_tokens
            low_actuals.append(act_tokens)
        else:
            deep_path = get_cache_path("deep", f"pr_{pr.branch}", "default", PROMPT_VERSION)
            deep_data = read_cache(deep_path)
            if not deep_data:
                missing = True
                continue
            val = deep_data.get("usage", {}).get("total_tokens", 0)
            baseline += val
            actual += val
            high_actuals.append(val)
            
    if missing or baseline == 0:
        return {
            "baseline_tokens": None,
            "actual_tokens": None,
            "savings": None,
            "mean_low": None,
            "mean_high": None,
            "n": len(prs)
        }
        
    savings = max(0, 1.0 - (actual / baseline))
    return {
        "baseline_tokens": baseline,
        "actual_tokens": actual,
        "savings": savings,
        "mean_low": sum(low_actuals) / len(low_actuals) if low_actuals else 0,
        "mean_high": sum(high_actuals) / len(high_actuals) if high_actuals else 0,
        "n": len(prs)
    }

def project_savings(mean_low: float, mean_high: float, low_share: float) -> float:
    if mean_high == 0:
        return 0.0
    projected_actual = (mean_low * low_share) + (mean_high * (1.0 - low_share))
    projected_baseline = mean_high
    return max(0, 1.0 - (projected_actual / projected_baseline))
