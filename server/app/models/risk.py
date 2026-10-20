from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskSignal(BaseModel):
    signal_type: str
    count: int
    impact_score: int
    reason: str
    associated_ids: List[str] = Field(default_factory=list)

class RiskScoreResponse(BaseModel):
    case_id: str
    score: int
    risk_level: RiskLevel
    signals: List[RiskSignal]
    explanation: str
    calculated_at: datetime

class AIAnalysisResponse(BaseModel):
    case_id: str
    summary: str
    risk_explanation: str
    facts: List[str]
    ai_interpretations: List[str]
    detected_attack_patterns: List[str]
    investigation_considerations: List[str]
    ai_provider: str
    is_fallback: bool
    generated_at: datetime

class ForensicRecommendation(BaseModel):
    recommendation_id: str
    title: str
    description: str
    reason: str
    severity: str
    source_signals: List[str]
    action_category: str
    created_at: datetime

class RecommendationsResponse(BaseModel):
    case_id: str
    total_recommendations: int
    recommendations: List[ForensicRecommendation]

class GlobalRiskStats(BaseModel):
    average_risk_score: float
    critical_risk_cases: int
    high_risk_cases: int
    moderate_risk_cases: int
    low_risk_cases: int
    total_assessed_cases: int
