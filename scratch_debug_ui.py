from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app.py")
at.run(timeout=10)
print(at.session_state)
