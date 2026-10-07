with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

details_code = """
        st.markdown("### File Changes")
        from rex.gitdata import get_merge_base, get_diff_numstat, get_added_lines_and_diff_text
        merge_base = get_merge_base(repo, pr.branch)
        numstat = get_diff_numstat(repo, merge_base, pr.branch)
        
        file_changes = [{"File": path, "Added": add, "Deleted": rem, "Total Lines": add + rem} for add, rem, path in numstat]
        st.dataframe(pd.DataFrame(file_changes), use_container_width=True, hide_index=True)
        
        st.markdown("### Pull Request Diff")
        _, diff_text = get_added_lines_and_diff_text(repo, merge_base, pr.branch)
        st.code(diff_text, language="diff")
        
"""

# Insert before the button
target = '        if st.button("Approving as a senior", type="primary", use_container_width=True):'
content = content.replace(target, details_code + target)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done details")
