from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, Optional
from app.core.database import get_database
from app.routers.auth import get_current_user
from app.core.rbac import is_admin, require_case_access, get_accessible_case_ids, can_view_all_cases
from app.models.graph import EvidenceGraphResponse
from app.models.risk import (
    RiskScoreResponse,
    AIAnalysisResponse,
    RecommendationsResponse,
    GlobalRiskStats
)
from app.repositories.case import CaseRepository
from app.services.graph_service import GraphService
from app.services.risk_service import RiskScoringService
from app.services.ai_service import ForensicAIService, RecommendationService

router = APIRouter(tags=["analytics"])

@router.get("/cases/risk/stats", response_model=GlobalRiskStats)
async def get_global_risk_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve global risk aggregates across accessible forensic cases for Dashboard."""
    db = get_database()
    allowed_case_ids = None
    if not can_view_all_cases(current_user):
        allowed_case_ids = await get_accessible_case_ids(db, current_user)
    return await RiskScoringService.get_global_risk_stats(db, allowed_case_ids=allowed_case_ids)

@router.get("/cases/{case_id}/graph", response_model=EvidenceGraphResponse)
async def get_case_evidence_graph(
    case_id: str,
    node_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate the real Evidence Graph representing topologically connected entities:
    Case -> Evidence -> Events -> Devices -> Investigators -> Locations.
    """
    db = get_database()
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CASE_NOT_FOUND")

    require_case_access(current_user, case)

    return await GraphService.build_case_graph(
        db=db,
        case_id=str(case["_id"]),
        node_type_filter=node_type,
        severity_filter=severity
    )

@router.get("/cases/{case_id}/risk-score", response_model=RiskScoreResponse)
async def get_case_risk_score(
    case_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Calculate deterministic, explainable forensic risk score (0-100)
    derived strictly from database evidence, custody failures, and timeline alerts.
    """
    db = get_database()
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CASE_NOT_FOUND")

    require_case_access(current_user, case)

    return await RiskScoringService.calculate_case_risk(db, str(case["_id"]))

@router.get("/cases/{case_id}/ai-analysis", response_model=AIAnalysisResponse)
async def get_case_ai_analysis(
    case_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate structured forensic AI intelligence and threat reasoning.
    Strictly distinguishes cryptographically verified FACTS from AI INTERPRETATIONS.
    Includes offline rule-based fallback when Gemini is unavailable.
    """
    db = get_database()
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CASE_NOT_FOUND")

    require_case_access(current_user, case)

    risk_data = await RiskScoringService.calculate_case_risk(db, str(case["_id"]))
    return await ForensicAIService.generate_case_analysis(db, str(case["_id"]), risk_data)

@router.get("/cases/{case_id}/recommendations", response_model=RecommendationsResponse)
async def get_case_recommendations(
    case_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieve signal-derived actionable investigative recommendations for a case.
    """
    db = get_database()
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CASE_NOT_FOUND")

    require_case_access(current_user, case)

    risk_data = await RiskScoringService.calculate_case_risk(db, str(case["_id"]))
    return await RecommendationService.generate_recommendations(db, str(case["_id"]), risk_data)

@router.post("/cases/{case_id}/recommendations/generate", response_model=RecommendationsResponse)
async def generate_case_recommendations(
    case_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Force re-evaluation of case findings to produce refreshed recommendations.
    """
    db = get_database()
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CASE_NOT_FOUND")

    require_case_access(current_user, case)

    risk_data = await RiskScoringService.calculate_case_risk(db, str(case["_id"]))
    return await RecommendationService.generate_recommendations(db, str(case["_id"]), risk_data)
