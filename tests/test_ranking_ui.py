import pytest
from streamlit.testing.v1 import AppTest

def test_ranking_issue_list(monkeypatch):
    at = AppTest.from_file("../app.py")
    
    # We can inject a mock option_menu into streamlit_option_menu module
    import streamlit_option_menu
    original_option_menu = streamlit_option_menu.option_menu
    
    def mock_option_menu(*args, **kwargs):
        # Always return "PR Ranking" for this test
        return "PR Ranking"
        
    monkeypatch.setattr(streamlit_option_menu, "option_menu", mock_option_menu)
    
    at.run(timeout=10)
    assert not at.exception
    
    # Should see the list
    md_texts = [md.value for md in at.markdown]
    assert any("Issue #42" in md for md in md_texts)
    
    # Click the "View" button for issue 42
    view_btns = [b for b in at.button if b.key == "view_issue_42"]
    assert len(view_btns) == 1
    view_btns[0].click().run(timeout=10)
    
    # Now should be in detail view
    assert any("Multi-PR Ranking Matrix (Issue #42)" in h.value for h in at.header)
    
    # Ensure no arrow_down bug
    md_texts_2 = [md.value for md in at.markdown]
    assert not any("arrow_down" in md for md in md_texts_2)
    
    # Back navigation
    back_btns = [b for b in at.button if "Back to issues" in b.label]
    assert len(back_btns) == 1
    back_btns[0].click().run(timeout=10)
    
    # Should be back on the issue list
    assert any("Issue Queue" in h.value for h in at.header)

def test_ranking_issue_list_99(monkeypatch):
    at = AppTest.from_file("../app.py")
    
    import streamlit_option_menu
    def mock_option_menu(*args, **kwargs):
        return "PR Ranking"
        
    monkeypatch.setattr(streamlit_option_menu, "option_menu", mock_option_menu)
    at.run(timeout=10)
    
    md_texts = [md.value for md in at.markdown]
    assert any("Issue #99" in md for md in md_texts)
    
    view_btns = [b for b in at.button if b.key == "view_issue_99"]
    view_btns[0].click().run(timeout=10)
    
    assert any("Single PR (No Competitors)" in s.value for s in at.subheader)
    
