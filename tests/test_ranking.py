import pytest
from rex.ranking import validate_bugs, get_git_ranking_metrics, rank_prs
from rex.config import RANKING_WEIGHTS
from rex.models import PRMetadata

def test_weights_sum():
    assert abs(sum(RANKING_WEIGHTS.values()) - 1.0) < 1e-9

def test_citation_validation():
    diff_map = {
        "file_a.py": {10, 11, 12},
        "file_b.py": {5}
    }
    
    bugs = [
        {"file": "file_a.py", "line": 11, "description": "valid"},
        {"file": "file_a.py", "line": 9, "description": "outside diff"},
        {"file": "file_c.py", "line": 1, "description": "wrong file"}
    ]
    
    valid, dropped = validate_bugs(bugs, diff_map)
    
    assert len(valid) == 1
    assert valid[0]["description"] == "valid"
    assert dropped == 2
