from streamlit.testing.v1 import AppTest
from rex.config import RISK_WEIGHTS

def test_pr_detail_low():
    at = AppTest.from_file("../app.py")
    at.query_params["pr_details"] = "pr_typo_fix"
    at.run(timeout=10)
    assert not at.exception
    
    md_texts = [md.value for md in at.markdown]
    assert any("pr_typo_fix" in md for md in md_texts)
    assert any("LOW RISK" in md for md in md_texts)
    assert any("One-click approval" in md for md in md_texts)
    assert "Approve" in [b.label for b in at.button]
    assert not any("Findings" in md for md in md_texts)

def test_pr_detail_high():
    at = AppTest.from_file("../app.py")
    at.query_params["pr_details"] = "pr_large_refactor"
    at.run(timeout=10)
    assert not at.exception
    
    md_texts = [md.value for md in at.markdown]
    assert any("HIGH RISK" in md for md in md_texts)
    assert any("Senior sign-off required" in md for md in md_texts)
    assert any("### Findings" in md for md in md_texts)

def test_pr_detail_forced():
    at = AppTest.from_file("../app.py")
    at.query_params["pr_details"] = "pr_secret_leak"
    at.run(timeout=10)
    assert not at.exception
    
    md_texts = [md.value for md in at.markdown]
    assert any("FORCED REVIEW" in md for md in md_texts)
    assert any("SECRET_CONTENT" in md for md in md_texts)
    err_texts = [e.value for e in at.error]
    assert any("Secret alert" in e for e in err_texts)

def test_pr_detail_injection():
    at = AppTest.from_file("../app.py")
    at.query_params["pr_details"] = "pr_injection_low"
    at.run(timeout=10)
    assert not at.exception
    
    md_texts = [md.value for md in at.markdown]
    assert any("Attack Detected" in md for md in md_texts)
    
def test_pr_competing():
    at = AppTest.from_file("../app.py")
    at.query_params["pr_details"] = "pr_issue42_a"
    at.run(timeout=10)
    assert not at.exception
    
    labels = [b.label for b in at.button]
    assert any("Competing" in l for l in labels)
