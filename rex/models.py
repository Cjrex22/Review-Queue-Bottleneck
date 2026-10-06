from pydantic import BaseModel
from typing import List, Optional, Dict

class PRMetadata(BaseModel):
    branch: str
    head_sha: str
    title: str
    body: str
    issue: Optional[str] = None

class RawFeatures(BaseModel):
    files: int
    dirs: int
    lines: int
    entropy: float
    prior_defect_density: float

class NormalizedFeatures(BaseModel):
    files_touched: float
    dirs_touched: float
    lines: float
    entropy: float
    prior_defect_density: float

class OverrideResults(BaseModel):
    reasons: List[str]
    injection_detected: bool

class RiskResult(BaseModel):
    raw_features: RawFeatures
    normalized_features: NormalizedFeatures
    risk_score: float
    overrides: OverrideResults
    label: str
    tier: str
