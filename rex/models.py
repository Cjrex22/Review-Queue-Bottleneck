from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

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

class SummaryReview(BaseModel):
    summary: str
    change_type: str

class Finding(BaseModel):
    file: str
    line: int
    severity: str
    comment: str

class DeepReview(BaseModel):
    summary: str
    flag_reasons: List[str]
    findings: List[Finding]

class BugFinding(BaseModel):
    file: str
    line: int
    description: str

class RankingReview(BaseModel):
    requirement_completeness: int
    architectural_alignment: int
    time_complexity_notes: str
    memory_notes: str
    bugs_found: List[BugFinding]
    why_ranked_higher_or_lower: str

class UsageTokens(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class CacheEntry(BaseModel):
    head_sha: Optional[str] = None
    head_shas: Optional[Dict[str, str]] = None
    prompt_version: str
    model: str
    recorded_at: str
    usage: UsageTokens
    provider: str
    response: Any
