import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

start_idx = content.find('@st.dialog("PR Details", width="large")')
end_idx = content.find("if 'pr_details' in st.query_params:")

new_func = """@st.dialog("PR Details", width="large")
def show_pr_details(pr_branch):
    pr = next(p for p in prs if p.branch == pr_branch)
    risk = calculate_risk(repo, pr.branch, pr.title, pr.body)
    res = route_review(repo, pr, risk, counterfactual=False)
    summary = res.get("summary", "No summary available.") if not "error" in res else "Error loading cache"
    
    # 1. ALWAYS VISIBLE
    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown(f"<div style='font-size: 24px; font-weight: 600; margin-bottom: 8px;'>{pr.branch}</div>", unsafe_allow_html=True)
        if risk.tier == "LOW":
            badge = '<span style="border: 1px solid rgba(63, 185, 80, 0.4); color: #3fb950; padding: 2px 10px; border-radius: 12px; font-weight: 600; font-size: 12px;">🟢 LOW RISK</span>'
            action = "One-click approval"
        elif risk.overrides.reasons:
            badge = '<span style="border: 1px solid rgba(248, 81, 73, 0.4); color: #f85149; padding: 2px 10px; border-radius: 12px; font-weight: 600; font-size: 12px;">🔴 FORCED REVIEW</span>'
            action = f"Senior sign-off required — {', '.join(risk.overrides.reasons)}"
        else:
            badge = '<span style="border: 1px solid rgba(210, 153, 34, 0.4); color: #d29922; padding: 2px 10px; border-radius: 12px; font-weight: 600; font-size: 12px;">🟡 HIGH RISK</span>'
            action = "Senior sign-off required"
            
        inj = ""
        if risk.overrides.injection_detected:
            inj = '<span style="margin-left: 8px; border: 1px solid rgba(248, 81, 73, 0.4); color: #f85149; padding: 2px 10px; border-radius: 12px; font-weight: 600; font-size: 12px;">⚠️ Attack Detected</span>'
            
        st.markdown(f"{badge}{inj}", unsafe_allow_html=True)
        st.markdown(f"<div style='margin-top: 8px; font-size: 14px; color: #8b949e;'>{action}</div>", unsafe_allow_html=True)
        
    with cols[1]:
        st.markdown(f"<div style='text-align: right; font-size: 32px; font-weight: 700; color: #c9d1d9;'>{risk.risk_score:.2f}</div>", unsafe_allow_html=True)

    # Competing badge
    if pr.issue:
        issue_prs = [p for p in prs if p.issue == pr.issue]
        if len(issue_prs) >= 2:
            shas = {p.branch: p.head_sha for p in issue_prs}
            cache_ab = check_cache("ranking", f"issue_{pr.issue}", "AB", PROMPT_VERSION, expected_shas=shas)
            cache_ba = check_cache("ranking", f"issue_{pr.issue}", "BA", PROMPT_VERSION, expected_shas=shas)
            if cache_ab and cache_ba and cache_ab != "CACHE_MISS_STALE" and cache_ba != "CACHE_MISS_STALE":
                res_rank = rank_prs(repo, pr.issue, issue_prs, cache_ab["response"], cache_ba["response"])
                rank = next((p.rank for p in res_rank.recommended_review_order if p.branch == pr.branch), None)
                if rank:
                    if st.button(f"🏆 Competing — Issue #{pr.issue}, ranked #{rank} of {len(issue_prs)}"):
                        st.session_state.current_tab = "PR Ranking"
                        st.rerun()

    st.divider()

    import pandas as pd
    contribs = {
        "lines": risk.normalized_features.lines * RISK_WEIGHTS["lines"],
        "files_touched": risk.normalized_features.files_touched * RISK_WEIGHTS["files_touched"],
        "dirs_touched": risk.normalized_features.dirs_touched * RISK_WEIGHTS["dirs_touched"],
        "entropy": risk.normalized_features.entropy * RISK_WEIGHTS["entropy"],
        "prior_defect_density": risk.normalized_features.prior_defect_density * RISK_WEIGHTS["prior_defect_density"]
    }

    if risk.tier == "LOW":
        st.write(summary)
        with st.expander("Why this score?"):
            bd = [{"Feature": k, "Weight": RISK_WEIGHTS[k], "Norm Value": getattr(risk.normalized_features, k), "Contribution": v} for k, v in contribs.items()]
            st.dataframe(pd.DataFrame(bd), use_container_width=True, hide_index=True)
        if st.button("Approve", type="primary", use_container_width=True):
            st.success("Approved!")
    else:
        st.write(summary)
        
        # Flag reasons
        if risk.overrides.reasons:
            st.markdown(f"**Flag Reasons:** {', '.join(risk.overrides.reasons)}")
        else:
            top_features = sorted(contribs.items(), key=lambda x: x[1], reverse=True)
            top_names = [k for k, v in top_features[:2]]
            st.markdown(f"**Flag Reasons:** High risk score driven by {', '.join(top_names)}")

        st.markdown("### Findings")
        findings = res.get("findings", []) if not "error" in res else []
        if not findings:
            st.write("No findings recorded")
        else:
            for f in findings:
                st.markdown(f"**{f.get('file')}:{f.get('line')}** [{f.get('severity')}] — {f.get('comment')}")

        secrets = [r for r in risk.overrides.reasons if "SECRET_CONTENT" in r]
        if secrets:
            for s in secrets:
                st.error(f"Secret alert: {s}")

        with st.expander("Why this score?"):
            bd = [{"Feature": k, "Weight": RISK_WEIGHTS[k], "Norm Value": getattr(risk.normalized_features, k), "Contribution": v} for k, v in contribs.items()]
            st.dataframe(pd.DataFrame(bd), use_container_width=True, hide_index=True)
            
        st.button("Senior sign-off required", disabled=True, use_container_width=True)

"""

new_content = content[:start_idx] + new_func + "\n" + content[end_idx:]

with open("app.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Done rewrite")
