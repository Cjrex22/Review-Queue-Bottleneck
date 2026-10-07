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
import subprocess
import time
from streamlit_option_menu import option_menu

st.set_page_config(page_title="REX Review Gate", layout="wide")

st.markdown("""
    <style>
    /* Apply GitHub's native system font stack globally */
    html, body, [class*="css"], [class*="st-"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji" !important;
    }
    /* Reduce top padding to push nav bar up */
    .block-container {
        padding-top: 1.5rem !important;
    }
    /* Hide the deploy button, keep the three-dot menu */
    [data-testid="stAppDeployButton"] {
        display: none !important;
    }
    /* Make the native header transparent so it doesn't clip the nav bar */
    [data-testid="stHeader"] {
        background-color: transparent !important;
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
            "margin-bottom": "5px",
            "border": "1px solid rgba(255, 255, 255, 0.1)"
        },
        "icon": {"color": "white", "font-size": "18px"}, 
        "nav-link": {
            "font-family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji'",
            "color": "white", 
            "font-size": "16px", 
            "text-align": "center", 
            "margin": "5px", 
            "border-radius": "50px",
            "--hover-color": "rgba(255, 255, 255, 0.1)"
        },
        "nav-link-selected": {"background-color": "#238636"},
    }
)

def get_git_repo_info():
    try:
        # Ask Git for the remote origin URL
        result = subprocess.run(["git", "config", "--get", "remote.origin.url"], capture_output=True, text=True, check=True)
        url = result.stdout.strip()
        
        # Extract the owner/repo format from https or ssh URLs
        import re
        match = re.search(r'github\.com[:/](.+?)(?:\.git)?$', url)
        if match:
            repo_name = match.group(1)
            return repo_name, f"https://github.com/{repo_name}"
    except Exception:
        pass
    
    # Fallback if not pushed to a remote yet
    return "local-repository", "#"

# Initialize state
if "current_tab" not in st.session_state:
    st.session_state.current_tab = selected
if "is_loading" not in st.session_state:
    st.session_state.is_loading = False

# 1. Detect tab change and trigger load state
if st.session_state.current_tab != selected:
    st.session_state.current_tab = selected
    st.session_state.is_loading = True
    st.rerun()

# 2. Render ONLY the loader in isolation
if st.session_state.is_loading:
    st.session_state.is_loading = False
    st.markdown(
        """
        <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 60vh; gap: 15px;">
            <svg style="animation: spin 1s linear infinite; width: 40px; height: 40px; color: #238636;" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-opacity="0.2" stroke-width="2" vector-effect="non-scaling-stroke"></circle>
                <path d="M15 8a7.002 7.002 0 00-7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" vector-effect="non-scaling-stroke"></path>
            </svg>
            <span style="color: #888888; font-size: 14px; font-weight: 500;">Resolving Git deltas...</span>
        </div>
        <style>
            @keyframes spin { 100% { transform: rotate(360deg); } }
            header { visibility: hidden; } /* Hide Streamlit top decoration */
        </style>
        """,
        unsafe_allow_html=True
    )
    import time
    time.sleep(0.4)
    st.rerun()

# 3. Render the actual tab content ONLY when not loading
else:
    if selected == "Home":
        st.markdown("<h1 style='text-decoration: underline;'>REX Review Gate</h1>", unsafe_allow_html=True)
        st.markdown(
            """
            <style>
                .routing-btn {
                    display: flex !important;
                    align-items: center !important;
                    padding: 4px 12px !important;
                    font-size: 12px !important;
                    color: #888888 !important;
                    text-decoration: none !important;
                    border: 1px solid #333333 !important;
                    border-bottom: 1px solid #333333 !important;
                    border-radius: 20px !important;
                    background-color: transparent !important;
                    box-shadow: none !important;
                    transition: all 0.2s ease !important;
                    margin-top: 2px !important;
                }
                .routing-btn:hover {
                    color: #dddddd !important;
                    border-color: #666666 !important;
                    background-color: #1a1a1a !important;
                    text-decoration: none !important;
                }
            </style>
            <div style="display: flex; align-items: center; gap: 10px; margin-top: -5px; margin-bottom: 15px;">
                <div style="font-size: 1.75rem; font-weight: 600; margin: 0; padding: 0; line-height: 1.2;">Deterministic AI Routing Engine</div>
                <a href="#risk-tier-breakdown" class="routing-btn">
                    View Routing Logic ↓
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )
    
        st.info("**Math Before AI:** REX uses local Git metrics to calculate risk *first*, slashing API costs by reserving expensive LLM deep-reviews only for dangerous code.")
    
        # Clean "Currently Tracking" Header
        repo_name, repo_url = get_git_repo_info()

        st.markdown(
            f"""
            <div style="margin-top: 0px; margin-bottom: 20px;">
                <span style="font-size: 14px; font-weight: 500; color: #888888;">Currently Tracking: </span>
                <a href="{repo_url}" target="_blank" style="
                    color: #e6edf3; 
                    text-decoration: none; 
                    font-size: 15px; 
                    font-weight: 600; 
                    transition: color 0.2s;
                " onmouseover="this.style.color='#8b5cf6'; this.style.textDecoration='underline';" onmouseout="this.style.color='#e6edf3'; this.style.textDecoration='none';">
                    {repo_name}
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Flat README Renderer
        import os
        readme_path = "README.md"
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_content = f.read()
        
            st.markdown("---") # Visual divider
        
            # Render the floating badge completely independently
            badge_html = '''
            <div style="float: left; margin-top: 5px; margin-right: 15px; margin-bottom: 10px; font-size: 13px; font-weight: 500; color: #888888; border: 1px solid #333333; padding: 4px 10px; border-radius: 20px; display: inline-flex; align-items: center; gap: 6px;">
                <svg fill="currentColor" viewBox="0 0 16 16" width="14" height="14"><path d="M2 1.75C2 .784 2.784 0 3.75 0h5.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0 1 12.25 16h-8.5A1.75 1.75 0 0 1 2 14.25Zm1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25V4.664a.25.25 0 0 0-.073-.177l-2.914-2.914a.25.25 0 0 0-.177-.073ZM8 3.25a.75.75 0 0 1 .75.75v1.5h1.5a.75.75 0 0 1 0 1.5h-1.5v1.5a.75.75 0 0 1-1.5 0V7h-1.5a.75.75 0 0 1 0-1.5h1.5V4a.75.75 0 0 1 .75-.75Z"></path></svg>
                README.md
            </div>
            '''
            st.markdown(badge_html, unsafe_allow_html=True)
        
            # Render the pure markdown without unsafe HTML flags mixed in
            st.markdown(readme_content)
        else:
            st.warning("No README.md found in the root directory.")
        
        st.divider()

        st.markdown("### Risk Tier Breakdown")
        tier_data = {
            "Feature": [
                "Example PR", 
                "What the bot sees", 
                "Why it lands here", 
                "What the bot does", 
                "What the senior gets", 
                "Who must approve"
            ],
            "🟢 Low Risk (< 0.35)": [
                "Fix a typo in a README and rename a variable",
                "3 lines changed, 1 file",
                "Low score",
                "Posts a short AI summary only",
                "A 2-minute skim, low priority in the queue",
                "A human, but a quick one"
            ],
            "🟡 High Risk (≥ 0.35)": [
                "Rewrite the payment logic across 8 files",
                "400 lines changed, 8 files",
                "High score",
                "Posts the summary, the reasons for the flag, and line-by-line comments on the risky parts",
                "A flagged PR at the top of the queue, with the exact lines to check",
                "A senior engineer, and merge is blocked until they approve"
            ],
            "🔴 Forced Review (Override)": [
                "A 2-line change that hardcodes an API key",
                "Tiny change, so the score alone would say 'safe'",
                "A rule catches it, whatever the score says",
                "Same deep review as high risk, and it names the rule that fired",
                "An alert: 'possible secret exposed, review before merge'",
                "A senior engineer, and merge is blocked"
            ]
        }
        import pandas as pd
        df_tiers = pd.DataFrame(tier_data).set_index("Feature")
        st.table(df_tiers)

        st.markdown("### What Separates Them (Ranking Factors)")
        st.markdown("""
        - **Test Delta (Git):** Presence of added or modified tests.
        - **Blast Radius (Git):** The number of unique files and directories touched.
        - **Diff Efficiency (Git):** The raw number of lines changed.
        - **LLM Scoring Dimensions:** Requirement Completeness (0-3) and Architectural Alignment (0-3) drive the AI weighted sum.
        - **Decision-Support Evidence:** Time Complexity, Memory Management & Optimization, and Verified Bugs are extracted for deep review visibility, but do not mathematically alter the base ranking score.
        - **Positional Debiasing:** The engine evaluates PRs in both AB and BA order. Disagreements trigger a 'Low Confidence' human-in-the-loop fallback to prevent AI hallucination bias.
        """)

        st.divider()

    elif selected == "PR Inspector":
        st.title("Active Pull Requests")
        
        active_tab = st.session_state.get("pr_tier_menu", "Low Risk")
        tab_color = "#238636" # green
        if active_tab == "High Risk":
            tab_color = "#d29922" # yellow
        elif active_tab == "Forced Review":
            tab_color = "#f85149" # red

        pr_tab = option_menu(
            menu_title=None,
            options=["Low Risk", "High Risk", "Forced Review"],
            icons=["check-circle", "exclamation-triangle", "shield-exclamation"],
            default_index=0 if active_tab == "Low Risk" else 1 if active_tab == "High Risk" else 2,
            orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": "#0d1117", "border": "1px solid #30363d", "border-radius": "6px", "margin-bottom": "20px"},
                "icon": {"color": "white", "font-size": "16px"},
                "nav-link": {
                    "font-family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji'",
                    "font-size": "15px", 
                    "text-align": "center", 
                    "margin": "4px", 
                    "border-radius": "50px",
                    "color": "#c9d1d9",
                    "--hover-color": "rgba(255, 255, 255, 0.1)"
                },
                "nav-link-selected": {"background-color": tab_color, "color": "#ffffff"},
            },
            key="pr_tier_menu"
        )
        
        if active_tab != pr_tab:
            st.rerun()
        
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
    
        # Filter data based on the selected tab
        # Note: Assuming your dataframe has a 'Tier' column containing these keywords as seen in the UI
        if pr_tab == "Low Risk":
            filtered_df = df[df['Tier'].str.contains("LOW RISK", case=False, na=False)]
        elif pr_tab == "High Risk":
            filtered_df = df[df['Tier'].str.contains("HIGH RISK", case=False, na=False)]
        else:
            filtered_df = df[df['Tier'].str.contains("FORCED REVIEW", case=False, na=False)]
            
        # Render the filtered table (Temporary until next UI iteration)
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"No {pr_tab.lower()} pull requests in the queue.")

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
