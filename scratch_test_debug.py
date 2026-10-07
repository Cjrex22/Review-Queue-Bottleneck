from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app.py")
at.query_params["pr_details"] = "pr_typo_fix"
at.run(timeout=10)
print("Markdowns:")
for i, md in enumerate(at.markdown):
    print(f"[{i}] {md.value[:50]}")
