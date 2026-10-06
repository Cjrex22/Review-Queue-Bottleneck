import json
from pathlib import Path
from typing import Dict, Any, Optional

def get_cache_path(task: str, subject_id: str, variant: str, prompt_version: str) -> Path:
    return Path("demo_cache") / f"{task}__{subject_id}__{variant}__{prompt_version}.json"

def read_cache(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)

def write_cache(path: Path, entry: Dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(entry, f, indent=2)

def check_cache(task: str, subject_id: str, variant: str, prompt_version: str, expected_sha: str = None, expected_shas: Dict[str, str] = None) -> Any:
    path = get_cache_path(task, subject_id, variant, prompt_version)
    data = read_cache(path)
    if not data:
        return None
        
    if expected_sha and data.get("head_sha") != expected_sha:
        return "CACHE_MISS_STALE"
        
    if expected_shas and data.get("head_shas") != expected_shas:
        return "CACHE_MISS_STALE"
        
    return data
