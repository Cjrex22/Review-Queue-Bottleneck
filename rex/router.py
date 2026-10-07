import os
from datetime import datetime, timezone
from .models import RiskResult, SummaryReview, DeepReview, PRMetadata, CacheEntry
from .prompts import SYSTEM_PROMPT, SUMMARY_PROMPT, DEEP_PROMPT, wrap_untrusted
from .llm import call_llm
from .cache import check_cache, write_cache, get_cache_path
from .config import PROMPT_VERSION

def route_review(repo, pr: PRMetadata, risk: RiskResult, force_deep: bool = False, counterfactual: bool = False):
    model = os.getenv("REX_MODEL", "gpt-4o-mini")
    
    from .gitdata import get_added_lines_and_diff_text, get_merge_base
    merge_base = get_merge_base(repo, pr.branch)
    _, diff = get_added_lines_and_diff_text(repo, merge_base, pr.branch)
    
    data_text = f"Title: {pr.title}\nBody: {pr.body}\nDiff:\n{diff}"
    data_text = wrap_untrusted(data_text)
    
    if counterfactual:
        task = "counterfactual_deep"
        prompt = DEEP_PROMPT.format(data=data_text, summary_length="4-5 lines")
    elif risk.tier == "LOW" and not force_deep:
        task = "summary"
        prompt = SUMMARY_PROMPT.format(data=data_text)
    else:
        task = "deep"
        if risk.overrides.reasons:
            s_len = "2-3 lines"
        else:
            s_len = "4-5 lines"
        prompt = DEEP_PROMPT.format(data=data_text, summary_length=s_len)
        
    subject_id = f"pr_{pr.branch}"
    cached = check_cache(task, subject_id, "default", PROMPT_VERSION, expected_sha=pr.head_sha)
    
    if cached == "CACHE_MISS_STALE":
        return {"error": "CACHE_MISS_STALE"}
    if cached:
        return cached["response"]
        
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    res = call_llm(messages, model)
    if not res.get("success"):
        return {"error": res.get("error_code")}
        
    entry = {
        "head_sha": pr.head_sha,
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "usage": res["usage"],
        "provider": res["provider"],
        "response": res["response"]
    }
    write_cache(get_cache_path(task, subject_id, "default", PROMPT_VERSION), entry)
    
    return res["response"]

def record_ranking(repo, issue: str, cand1: PRMetadata, cand2: PRMetadata, order: str):
    from .prompts import RANKING_PROMPT
    from .gitdata import get_added_lines_and_diff_text, get_merge_base
    
    model = os.getenv("REX_MODEL", "gpt-4o-mini")
    
    def get_cand_text(c: PRMetadata):
        mb = get_merge_base(repo, c.branch)
        _, diff = get_added_lines_and_diff_text(repo, mb, c.branch)
        return wrap_untrusted(diff)
        
    c1_text = get_cand_text(cand1)
    c2_text = get_cand_text(cand2)
    
    prompt = RANKING_PROMPT.format(cand1=c1_text, cand2=c2_text)
    task = "ranking"
    subject_id = f"issue_{issue}"
    variant = order
    
    shas = {cand1.branch: cand1.head_sha, cand2.branch: cand2.head_sha}
    
    cached = check_cache(task, subject_id, variant, PROMPT_VERSION, expected_shas=shas)
    if cached == "CACHE_MISS_STALE":
        return {"error": "CACHE_MISS_STALE"}
    if cached:
        return cached["response"]
        
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    res = call_llm(messages, model)
    if not res.get("success"):
        return {"error": res.get("error_code")}
        
    entry = {
        "head_shas": shas,
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "usage": res["usage"],
        "provider": res["provider"],
        "response": res["response"]
    }
    write_cache(get_cache_path(task, subject_id, variant, PROMPT_VERSION), entry)
    
    return res["response"]
