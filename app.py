import streamlit as st
import json
from pathlib import Path
from rex.models import PRMetadata
from rex.risk import calculate_risk
from rex.router import route_review
from rex.ranking import rank_prs
from rex.cache import check_cache
from rex.config import PROMPT_VERSION, RANKING_WEIGHTS
from rex.tokens import calculate_savings, project_savings
import os

st.set_page_config(page_title="REX Review Gate", layout="wide")

repo = Path("data/fixture_repo")
manifest_path = Path("data/manifest.json")

if not manifest_path.exists():
    st.error("Manifest not found. Run scripts/build_fixtures.py")
    st.stop()

with open(manifest_path) as f:
    manifest = json.load(f)
    
prs = [PRMetadata(**p) for p in manifest["prs"]]

st.title("REX Review Gate")

tab1, tab2, tab3 = st.tabs(["Triage Gate & PR Inspector", "Multi-PR Ranking Matrix (Issue #42)", "Token Economics & ROI Calculator"])

with tab1:
    st.header("Triage Gate & PR Inspector")
    
    selected_pr_branch = st.selectbox("Select PR to inspect", [p.branch for p in prs])
    pr = next(p for p in prs if p.branch == selected_pr_branch)
    
    risk = calculate_risk(repo, pr.branch, pr.title, pr.body)
    
    cols = st.columns(4)
    cols[0].metric("Risk Score", f"{risk.risk_score:.2f}")
    if risk.tier == "LOW":
        cols[1].metric("Tier", "🟢 LOW RISK")
    elif risk.overrides.reasons:
        cols[1].metric("Tier", "🔴 FORCED REVIEW")
    else:
        cols[1].metric("Tier", "🟡 HIGH RISK")
    
    override_text = ", ".join(risk.overrides.reasons) if risk.overrides.reasons else "None"
    cols[2].metric("Overrides", override_text)
    cols[3].metric("Hassan Entropy", f"{risk.raw_features.entropy:.2f}")
    
    if risk.overrides.injection_detected:
        st.warning("⚠️ Untrusted diff boundary injection detected in this PR.")
    
    st.subheader("LLM Review Card")
    res = route_review(repo, pr, risk, counterfactual=False)
    
    if "error" in res:
        st.error(f"Cache miss or error: {res['error']}")
    else:
        st.write("**Summary:**", res.get("summary", ""))
        
        if risk.tier != "LOW":
            st.write("**Flag Reasons:**")
            for reason in res.get("flag_reasons", []):
                st.markdown(f"- {reason}")
                
            st.write("**Verified Bug Citations:**")
            findings = res.get("findings", [])
            if not findings:
                st.write("No findings.")
            else:
                for f in findings:
                    st.info(f"**{f.get('file')}:{f.get('line')}** [{f.get('severity')}] - {f.get('comment')}")

with tab2:
    st.header("Multi-PR Ranking Matrix (Issue #42)")
    
    issue_prs = [p for p in prs if p.issue == "42"]
    if len(issue_prs) != 2:
        st.error("Need exactly 2 PRs for issue 42.")
    else:
        shas = {issue_prs[0].branch: issue_prs[0].head_sha, issue_prs[1].branch: issue_prs[1].head_sha}
        cache_ab = check_cache("ranking", "issue_42", "AB", PROMPT_VERSION, expected_shas=shas)
        cache_ba = check_cache("ranking", "issue_42", "BA", PROMPT_VERSION, expected_shas=shas)
        
        if not cache_ab or not cache_ba or cache_ab == "CACHE_MISS_STALE" or cache_ba == "CACHE_MISS_STALE":
            st.error("Missing or stale cache for ranking. Run record_cache.py")
        else:
            res = rank_prs(repo, "42", issue_prs, cache_ab["response"], cache_ba["response"])
            
            st.subheader("Recommended Review Order")
            for p in res.recommended_review_order:
                with st.expander(f"Rank {p.rank}: {p.branch} (Score: {p.total_score:.2f})", expanded=True):
                    if p.confidence == "LOW":
                        st.warning("LOW CONFIDENCE: Model disagreed with itself across orderings")
                    else:
                        st.success("HIGH CONFIDENCE: Debiased consensus reached.")
                        
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Git Metrics**")
                        st.write(f"- Test Delta: {p.test_delta_score} (W: {RANKING_WEIGHTS['test_delta_score']})")
                        st.write(f"- Blast Radius: {p.blast_radius_score} (W: {RANKING_WEIGHTS['blast_radius_score']})")
                        st.write(f"- Diff Efficiency: {p.diff_efficiency_score} (W: {RANKING_WEIGHTS['diff_efficiency_score']})")
                    with col2:
                        st.write("**LLM Rubrics**")
                        st.write(f"- Requirement Completeness: {p.requirement_completeness}")
                        st.write(f"- Architectural Alignment: {p.architectural_alignment}")
                        
                    st.write("**Evidence Text:**")
                    st.write(f"- **Time Complexity:** {p.time_complexity_notes}")
                    st.write(f"- **Memory:** {p.memory_notes}")
                    st.write(f"- **Why:** {p.why_ranked_higher_or_lower}")
                    
                    st.write(f"**Verified Bug Citations ({len(p.bugs_found)} kept, {p.dropped_findings_count} dropped):**")
                    for bug in p.bugs_found:
                        st.error(f"**BUG** at {bug.file}:{bug.line} - {bug.description}")

with tab3:
    st.header("Token Economics & ROI Calculator")
    
    res = calculate_savings(repo, prs)
    
    if res["savings"] is None:
        st.error("Missing cache. Run record_cache.py")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Baseline Tokens (Naive Deep Review)", res["baseline_tokens"])
        col2.metric("Actual Tokens (REX Routed)", res["actual_tokens"])
        col3.metric(f"RECORDED SAVINGS (n={res['n']})", f"{res['savings']*100:.1f}%")
        
        st.divider()
        st.subheader("Enterprise Projection")
        st.write(f"Based on measured tier means: LOW={res['mean_low']:.0f}, HIGH={res['mean_high']:.0f}")
        
        low_share = st.slider("Projected share of LOW risk PRs", 0.0, 1.0, 0.7)
        proj = project_savings(res["mean_low"], res["mean_high"], low_share)
        
        st.metric(f"PROJECTION: Savings at {low_share*100:.0f}% LOW share", f"{proj*100:.1f}%")
        st.code("1.0 - ((mean_low * low_share + mean_high * (1.0 - low_share)) / mean_high)")
