with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

target = """                if st.button("View PR Details", key="view_single_pr_details"):
                    st.query_params["pr_details"] = pr.branch
                    st.rerun()"""
                    
content = content.replace(target, "")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
