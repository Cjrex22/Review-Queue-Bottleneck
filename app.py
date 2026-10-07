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
from streamlit_option_menu import option_menu

st.set_page_config(page_title="REX Review Gate", layout="wide")

st.markdown("""
    <style>
    /* Reduce top padding to push nav bar up */
    .block-container {
        padding-top: 4rem !important;
    }
    /* Hide the deploy button, keep the three-dot menu */
    [data-testid="stAppDeployButton"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

repo = Path("data/fixture_repo")
manifest_path = Path("data/manifest.json")

if not manifest_path.exists():
    st.error("Manifest not found. Run scripts/build_fixtures.py")
    st.stop()

with open(manifest_path) as f:
    manifest = json.load(f)
    
prs = [PRMetadata(**p) for p in manifest["prs"]]

@st.dialog("PR Details", width="large")
def show_pr_details(pr_branch):
    pr = next(p for p in prs if p.branch == pr_branch)
    risk = calculate_risk(repo, pr.branch, pr.title, pr.body)
    
    st.subheader(f"Analysis for: {pr.branch}")
    st.caption("Contributor Name: [REDACTED PER SYSTEM RULE 8]")
    
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
        st.write("**Full Summary:**")
        st.info(res.get("summary", ""))
        
        if risk.tier != "LOW":
            st.write("**🔴 Flag Reasons (Red Flags):**")
            for reason in res.get("flag_reasons", []):
                st.markdown(f"- ❌ {reason}")
                
            st.write("**Verified Bug Citations:**")
            findings = res.get("findings", [])
            if not findings:
                st.success("✅ No findings.")
            else:
                for f in findings:
                    st.error(f"**{f.get('file')}:{f.get('line')}** [{f.get('severity')}] - {f.get('comment')}")
        else:
            st.success("✅ No red flags detected (LOW RISK).")
            
    st.divider()
    st.subheader("File Changes")
    from rex.gitdata import get_merge_base, get_diff_numstat, get_added_lines_and_diff_text
    merge_base = get_merge_base(repo, pr.branch)
    numstat = get_diff_numstat(repo, merge_base, pr.branch)
    
    import pandas as pd
    file_changes = [{"File": path, "Added": add, "Deleted": rem, "Total Lines": add + rem} for add, rem, path in numstat]
    st.dataframe(pd.DataFrame(file_changes), use_container_width=True, hide_index=True)
    
    st.subheader("Pull Request Diff")
    _, diff_text = get_added_lines_and_diff_text(repo, merge_base, pr.branch)
    st.code(diff_text, language="diff")

selected = option_menu(
    menu_title=None,
    options=["Home", "PR Inspector", "PR Ranking", "Economics & ROI"],
    icons=["house", "search", "bar-chart-line", "wallet2"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {
            "padding": "0!important", 
            "background-color": "rgba(25, 25, 25, 0.6)", 
            "backdrop-filter": "blur(15px)",
            "border-radius": "50px",
            "margin-bottom": "30px",
            "border": "1px solid rgba(255, 255, 255, 0.1)"
        },
        "icon": {"color": "white", "font-size": "18px"}, 
        "nav-link": {
            "color": "white", 
            "font-size": "16px", 
            "text-align": "center", 
            "margin": "5px", 
            "border-radius": "50px",
            "--hover-color": "rgba(255, 255, 255, 0.1)"
        },
        "nav-link-selected": {"background-color": "#8b5cf6"},
    }
)

if selected == "Home":
    st.title("REX Review Gate")
    st.markdown("### Deterministic AI Routing Engine")
    
    st.info("**Math Before AI**: REX is a local-first triage system that uses purely deterministic Git-history metrics to decide how much expensive LLM effort a PR earns before making a single API call.")
    
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🛡️ Risk-Aware Triaging")
        st.markdown("""
        - **FORCED REVIEW:** Overrides for sensitive paths (e.g. `auth/`) or exposed secrets. Merge blocked.
        - **HIGH RISK (Score ≥ 0.35):** Triggered by high churn, entropy, or blast radius. Merge blocked.
        - **LOW RISK (Score < 0.35):** Earns a cheap LLM summary and qualifies for one-click human approval.
        """)
        
    with col2:
        st.markdown("#### ⚖️ Explainable Ranking")
        st.markdown("""
        - **Frozen Weights:** Rank competing PRs without bias using fixed algorithmic parameters.
        - **Debiased Consensus:** LLM sub-scores are averaged across AB/BA orderings.
        - **Verifiable Evidence:** LLM bug findings are strictly validated against Git diff ranges.
        """)
        
    with col3:
        st.markdown("#### 🔒 Offline-First Enterprise")
        st.markdown("""
        - **Contributor Blindness:** Complete adherence to Rule 8 (no author data ingested).
        - **Injection Defense:** Robust boundary checks against untrusted PR payloads.
        - **Cached Engine:** Built natively for zero-latency replay and token ROI projection.
        """)

elif selected == "PR Inspector":
    st.header("Triage Gate & PR Inspector")
    
    table_data = []
    for p in prs:
        risk = calculate_risk(repo, p.branch, p.title, p.body)
        res = route_review(repo, p, risk, counterfactual=False)
        
        tier_label = risk.tier
        if risk.tier == "LOW":
            tier_label = "🟢 LOW RISK"
        elif risk.overrides.reasons:
            tier_label = "🔴 FORCED REVIEW"
        else:
            tier_label = "🟡 HIGH RISK"
            
        summary = res.get("summary", "") if not "error" in res else "Error loading cache"
        short_heading = summary.split('.')[0] + "." if summary and '.' in summary else summary
        
        table_data.append({
            "PR Name": p.branch,
            "Risk Score": round(risk.risk_score, 2),
            "Tier": tier_label,
            "Short Heading": short_heading
        })
        
    import pandas as pd
    df = pd.DataFrame(table_data)
    
    st.write("Select a PR from the table below to view detailed analysis:")
    event = st.dataframe(
        df,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun",
        hide_index=True
    )
    
    selected_rows = event.selection.rows
    if selected_rows:
        selected_idx = selected_rows[0]
        selected_pr_branch = df.iloc[selected_idx]["PR Name"]
        pr = next(p for p in prs if p.branch == selected_pr_branch)
        
        risk = calculate_risk(repo, pr.branch, pr.title, pr.body)
        
        st.divider()
        st.subheader(f"Analysis for: {pr.branch}")
        
        # NOTE: Contributor Name intentionally omitted to comply with AGENTS.md Rule 8
        st.caption("Contributor Name: [REDACTED PER SYSTEM RULE 8]")
        
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
            st.write("**Full Summary:**")
            st.info(res.get("summary", ""))
            
            if risk.tier != "LOW":
                st.write("**🔴 Flag Reasons (Red Flags):**")
                for reason in res.get("flag_reasons", []):
                    st.markdown(f"- ❌ {reason}")
                    
                st.write("**Verified Bug Citations:**")
                findings = res.get("findings", [])
                if not findings:
                    st.success("✅ No findings.")
                else:
                    for f in findings:
                        st.error(f"**{f.get('file')}:{f.get('line')}** [{f.get('severity')}] - {f.get('comment')}")
            else:
                st.success("✅ No red flags detected (LOW RISK).")
                
        st.divider()
        st.subheader("File Changes")
        from rex.gitdata import get_merge_base, get_diff_numstat, get_added_lines_and_diff_text
        merge_base_insp = get_merge_base(repo, pr.branch)
        numstat_insp = get_diff_numstat(repo, merge_base_insp, pr.branch)
        
        file_changes_insp = [{"File": path, "Added": add, "Deleted": rem, "Total Lines": add + rem} for add, rem, path in numstat_insp]
        st.dataframe(pd.DataFrame(file_changes_insp), use_container_width=True, hide_index=True)
        
        st.subheader("Pull Request Diff")
        _, diff_text_insp = get_added_lines_and_diff_text(repo, merge_base_insp, pr.branch)
        st.code(diff_text_insp, language="diff")

elif selected == "PR Ranking":
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

elif selected == "Economics & ROI":
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
