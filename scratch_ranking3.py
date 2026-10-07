with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    'st.markdown(f"**Branch:** {pr.branch}")',
    'st.markdown(f"**Branch:** <a href=\'?pr_details={pr.branch}\' target=\'_self\'>{pr.branch}</a>", unsafe_allow_html=True)'
)

content = content.replace(
    '''                                    if st.button("View PR Details", key=f"view_pr_details_{p.branch}"):
                                        st.query_params["pr_details"] = p.branch
                                        st.rerun()''',
    '''                                    st.markdown(f"<a href='?pr_details={p.branch}' target='_self' style='display:inline-block; margin-top:8px; font-weight:600; color:#58a6ff; text-decoration:none;'>View PR Details ({p.branch}) →</a>", unsafe_allow_html=True)'''
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated to use links")
