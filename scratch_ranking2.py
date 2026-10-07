with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if 'elif selected == "PR Ranking":' in line:
        start_idx = i
    elif 'elif selected == "Economics & ROI":' in line:
        end_idx = i
        break

new_ranking_code = """    elif selected == "PR Ranking":
        # Group PRs by issue
        from collections import defaultdict
        issues_map = defaultdict(list)
        for p in prs:
            if p.issue:
                issues_map[p.issue].append(p)
                
        if "selected_issue" not in st.session_state:
            st.session_state.selected_issue = None
            
        if st.session_state.selected_issue is None:
            st.header("Issue Queue")
            
            if not issues_map:
                st.info("No issues found in manifest.")
            else:
                for issue_id, issue_prs in issues_map.items():
                    title = issue_prs[0].title
                    count_text = f"{len(issue_prs)} competing PRs" if len(issue_prs) > 1 else "1 PR"
                    
                    with st.container(border=True):
                        cols = st.columns([4, 1])
                        with cols[0]:
                            st.markdown(f"### Issue #{issue_id}: {title}")
                            st.markdown(f"**{count_text}**")
                        with cols[1]:
                            if st.button("View", key=f"view_issue_{issue_id}", use_container_width=True):
                                st.session_state.selected_issue = issue_id
                                st.rerun()
                                
        else:
            issue_id = st.session_state.selected_issue
            issue_prs = issues_map.get(issue_id, [])
            
            if st.button("← Back to issues"):
                st.session_state.selected_issue = None
                st.rerun()
                
            st.header(f"Multi-PR Ranking Matrix (Issue #{issue_id})")
            
            if len(issue_prs) == 0:
                st.error("Issue not found.")
            elif len(issue_prs) == 1:
                pr = issue_prs[0]
                risk = calculate_risk(repo, pr.branch, pr.title, pr.body)
                res = route_review(repo, pr, risk, counterfactual=False)
                summary = res.get("summary", "No summary available.") if not "error" in res else "Error loading cache"
                
                st.subheader("Single PR (No Competitors)")
                st.markdown(f"**Branch:** {pr.branch}")
                st.markdown(f"**Risk Score:** {risk.risk_score:.2f} ({risk.tier})")
                st.write(summary)
                
                if st.button("View PR Details", key="view_single_pr_details"):
                    st.query_params["pr_details"] = pr.branch
                    st.rerun()
                    
            else:
                if len(issue_prs) != 2:
                    st.error("Currently only exactly 2 PRs are supported for ranking.")
                else:
                    shas = {issue_prs[0].branch: issue_prs[0].head_sha, issue_prs[1].branch: issue_prs[1].head_sha}
                    cache_ab = check_cache("ranking", f"issue_{issue_id}", "AB", PROMPT_VERSION, expected_shas=shas)
                    cache_ba = check_cache("ranking", f"issue_{issue_id}", "BA", PROMPT_VERSION, expected_shas=shas)
                
                    if not cache_ab or not cache_ba or cache_ab == "CACHE_MISS_STALE" or cache_ba == "CACHE_MISS_STALE":
                        st.error("Missing or stale cache for ranking. Run record_cache.py")
                    else:
                        res = rank_prs(repo, issue_id, issue_prs, cache_ab["response"], cache_ba["response"])
                    
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
                                    
                                    if st.button("View PR Details", key=f"view_pr_details_{p.branch}"):
                                        st.query_params["pr_details"] = p.branch
                                        st.rerun()
                                        
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

"""

new_lines = lines[:start_idx] + [new_ranking_code] + lines[end_idx:]
with open("app.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Done ranking rewrite")
