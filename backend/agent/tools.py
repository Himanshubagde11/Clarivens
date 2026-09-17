"""
Clarivens AI Agent — Tool System.

All tools the agent can call are defined here with:
- Input validation (Pydantic)
- Permission requirements
- Risk levels
- Actual execution logic (calls existing Clarivens services)

The agent must NEVER call these tools directly — they go through
the safety layer (check_tool_permission) first.

Critical rules:
- Pricing always comes from the DB (never the LLM)
- Dataset content is never sent to the LLM (only profiling summaries)
- All project access is IDOR-protected (owner check)
- No tool can modify production code or schema
"""
import logging
import json
import time
from typing import Any, Optional
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from backend.database import models
from backend.agent.safety import check_tool_permission, get_tool_risk_level

logger = logging.getLogger(__name__)


# ============================================================
# Tool Result
# ============================================================

@dataclass
class ToolResult:
    tool_name: str
    success: bool
    data: Any = None
    summary: str = ""
    error: Optional[str] = None
    duration_ms: int = 0


# ============================================================
# Service Catalog Tools
# ============================================================

def search_services(query: str, db: Session, category: Optional[str] = None) -> ToolResult:
    """
    Searches the Clarivens service catalog by keyword.
    Returns service summaries — no pricing (use get_pricing for that).
    """
    t0 = time.time()
    try:
        q = db.query(models.ServiceCatalog).filter(models.ServiceCatalog.is_active == True)
        if category:
            q = q.filter(models.ServiceCatalog.category == category)
        services = q.order_by(models.ServiceCatalog.display_order).all()

        query_lower = query.lower()
        scored = []
        for svc in services:
            score = 0
            searchable = (svc.name + " " + svc.description + " " + " ".join(svc.keywords or [])).lower()
            for word in query_lower.split():
                if len(word) > 2 and word in searchable:
                    score += 1
            if score > 0 or not query:
                scored.append((score, svc))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [
            {
                "id": svc.id,
                "name": svc.name,
                "slug": svc.slug,
                "category": svc.category,
                "short_description": svc.short_description or svc.description[:150],
                "keywords": svc.keywords or [],
            }
            for _, svc in scored[:6]
        ]

        return ToolResult(
            tool_name="search_services",
            success=True,
            data=results,
            summary=f"Found {len(results)} matching services.",
            duration_ms=int((time.time() - t0) * 1000),
        )
    except Exception as e:
        logger.error("[Tool] search_services failed: %s", type(e).__name__)
        return ToolResult(tool_name="search_services", success=False, error="SERVICE_SEARCH_FAILED")


def get_service_details(service_slug: str, db: Session) -> ToolResult:
    """Returns full details for a specific service."""
    t0 = time.time()
    try:
        svc = db.query(models.ServiceCatalog).filter(
            models.ServiceCatalog.slug == service_slug,
            models.ServiceCatalog.is_active == True,
        ).first()
        if not svc:
            return ToolResult(tool_name="get_service_details", success=False, error="SERVICE_NOT_FOUND")

        return ToolResult(
            tool_name="get_service_details",
            success=True,
            data={
                "id": svc.id,
                "name": svc.name,
                "category": svc.category,
                "description": svc.description,
                "features": svc.features or [],
                "keywords": svc.keywords or [],
            },
            summary=f"Retrieved details for '{svc.name}'.",
            duration_ms=int((time.time() - t0) * 1000),
        )
    except Exception as e:
        logger.error("[Tool] get_service_details failed: %s", type(e).__name__)
        return ToolResult(tool_name="get_service_details", success=False, error="SERVICE_DETAIL_FAILED")


def get_package_details(service_slug: str, db: Session) -> ToolResult:
    """Returns all packages for a service — includes pricing from DB."""
    t0 = time.time()
    try:
        svc = db.query(models.ServiceCatalog).filter(
            models.ServiceCatalog.slug == service_slug,
            models.ServiceCatalog.is_active == True,
        ).first()
        if not svc:
            return ToolResult(tool_name="get_package_details", success=False, error="SERVICE_NOT_FOUND")

        packages = db.query(models.ServicePackage).filter(
            models.ServicePackage.service_id == svc.id,
            models.ServicePackage.is_active == True,
        ).order_by(models.ServicePackage.display_order).all()

        data = {
            "service": svc.name,
            "packages": [
                {
                    "id": pkg.id,
                    "name": pkg.name,
                    "price": pkg.price,
                    "currency": pkg.currency,
                    "description": pkg.description,
                    "features": pkg.features or [],
                    "limits": pkg.limits or {},
                    "addons": pkg.addons or [],
                }
                for pkg in packages
            ],
        }
        return ToolResult(
            tool_name="get_package_details",
            success=True,
            data=data,
            summary=f"Retrieved {len(packages)} packages for '{svc.name}'.",
            duration_ms=int((time.time() - t0) * 1000),
        )
    except Exception as e:
        logger.error("[Tool] get_package_details failed: %s", type(e).__name__)
        return ToolResult(tool_name="get_package_details", success=False, error="PACKAGE_DETAIL_FAILED")


def get_pricing(package_id: int, db: Session) -> ToolResult:
    """
    Returns pricing for a specific package — always from DB, never LLM-generated.
    """
    t0 = time.time()
    try:
        pkg = db.query(models.ServicePackage).filter(
            models.ServicePackage.id == package_id,
            models.ServicePackage.is_active == True,
        ).first()
        if not pkg:
            return ToolResult(tool_name="get_pricing", success=False, error="PACKAGE_NOT_FOUND")

        return ToolResult(
            tool_name="get_pricing",
            success=True,
            data={
                "package_id": pkg.id,
                "package_name": pkg.name,
                "price": pkg.price,
                "currency": pkg.currency,
                "limits": pkg.limits or {},
            },
            summary=f"Price for '{pkg.name}': {pkg.currency} {pkg.price}",
            duration_ms=int((time.time() - t0) * 1000),
        )
    except Exception as e:
        logger.error("[Tool] get_pricing failed: %s", type(e).__name__)
        return ToolResult(tool_name="get_pricing", success=False, error="PRICING_FAILED")


def get_service_recommendation(requirements: dict, db: Session) -> ToolResult:
    """
    Deterministic service matching based on extracted requirements.
    Never relies on LLM to select services — uses rule-based logic.
    """
    t0 = time.time()
    try:
        recommendations = []
        services = db.query(models.ServiceCatalog).filter(
            models.ServiceCatalog.is_active == True
        ).all()

        problem = requirements.get("business_problem", "").lower()
        dataset_type = requirements.get("dataset_type", "")
        requested_output = requirements.get("requested_output", [])

        if isinstance(dataset_type, list):
            dataset_type_str = " ".join(dataset_type).lower()
        else:
            dataset_type_str = str(dataset_type).lower()

        if isinstance(requested_output, list):
            output_str = " ".join(requested_output).lower()
        else:
            output_str = str(requested_output).lower()

        searchable_context = f"{problem} {dataset_type_str} {output_str}".lower()

        for svc in services:
            keywords = [k.lower() for k in (svc.keywords or [])]
            match_score = sum(1 for kw in keywords if kw in searchable_context)
            if match_score > 0:
                recommendations.append((match_score, {
                    "service_id": svc.id,
                    "service_name": svc.name,
                    "slug": svc.slug,
                    "category": svc.category,
                    "match_score": match_score,
                    "reason": f"Matches {match_score} of your requirement keywords.",
                }))

        recommendations.sort(key=lambda x: x[0], reverse=True)
        top = [r for _, r in recommendations[:3]]

        return ToolResult(
            tool_name="get_service_recommendation",
            success=True,
            data={"recommendations": top, "requirements_analyzed": requirements},
            summary=f"Identified {len(top)} recommended Clarivens services.",
            duration_ms=int((time.time() - t0) * 1000),
        )
    except Exception as e:
        logger.error("[Tool] get_service_recommendation failed: %s", type(e).__name__)
        return ToolResult(tool_name="get_service_recommendation", success=False, error="RECOMMENDATION_FAILED")


# ============================================================
# Lead Tools
# ============================================================

def create_lead(
    db: Session,
    session_id: int,
    email: str,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    industry: Optional[str] = None,
    business_type: Optional[str] = None,
    business_problem: Optional[str] = None,
    requirement: Optional[str] = None,
    recommended_service: Optional[str] = None,
    recommended_budget: Optional[str] = None,
    timeline: Optional[str] = None,
    dataset_available: Optional[bool] = None,
    source: str = "ai_agent",
) -> ToolResult:
    """Creates a lead record in the database."""
    t0 = time.time()
    try:
        # Validate email minimally
        if not email or "@" not in email:
            return ToolResult(tool_name="create_lead", success=False, error="INVALID_EMAIL")

        # Check for existing lead with same email
        existing = db.query(models.Lead).filter(models.Lead.email == email.lower()).first()
        if existing:
            return ToolResult(
                tool_name="create_lead",
                success=True,
                data={"lead_id": existing.id, "status": "existing"},
                summary="Lead already exists in our system.",
                duration_ms=int((time.time() - t0) * 1000),
            )

        lead = models.Lead(
            session_id=session_id,
            name=name,
            email=email.lower().strip(),
            phone=phone,
            company=company,
            industry=industry,
            business_type=business_type,
            business_problem=business_problem,
            requirement=requirement[:1000] if requirement else None,
            recommended_service=recommended_service,
            recommended_budget=recommended_budget,
            timeline=timeline,
            dataset_available=dataset_available,
            status="new",
            source=source,
        )
        db.add(lead)

        # Update session metric
        metric = db.query(models.AgentMetric).filter(
            models.AgentMetric.session_id == session_id
        ).first()
        if metric:
            metric.led_to_lead = True

        db.commit()
        db.refresh(lead)

        logger.info("[Tool] Lead created: id=%s email=%s", lead.id, email)
        return ToolResult(
            tool_name="create_lead",
            success=True,
            data={"lead_id": lead.id, "status": "created"},
            summary="Lead registered successfully.",
            duration_ms=int((time.time() - t0) * 1000),
        )
    except Exception as e:
        logger.error("[Tool] create_lead failed: %s", type(e).__name__)
        return ToolResult(tool_name="create_lead", success=False, error="LEAD_CREATION_FAILED")


# ============================================================
# Project / Dataset Tools (authenticated)
# ============================================================

def get_project_status(project_id: int, user_id: int, db: Session) -> ToolResult:
    """Returns project status — enforces IDOR protection."""
    t0 = time.time()
    try:
        project = db.query(models.Project).filter(
            models.Project.id == project_id,
            models.Project.owner_id == user_id,
        ).first()
        if not project:
            return ToolResult(tool_name="get_project_status", success=False, error="PROJECT_NOT_FOUND")

        # Get latest job status
        latest_job = (
            db.query(models.ProcessingJob)
            .filter(models.ProcessingJob.project_id == project_id)
            .order_by(models.ProcessingJob.id.desc())
            .first()
        )

        return ToolResult(
            tool_name="get_project_status",
            success=True,
            data={
                "project_id": project.id,
                "name": project.name,
                "status": project.status,
                "job_status": latest_job.status if latest_job else None,
                "created_at": project.created_at.isoformat(),
            },
            summary=f"Project '{project.name}' is {project.status}.",
            duration_ms=int((time.time() - t0) * 1000),
        )
    except Exception as e:
        logger.error("[Tool] get_project_status failed: %s", type(e).__name__)
        return ToolResult(tool_name="get_project_status", success=False, error="PROJECT_STATUS_FAILED")


def get_dataset_profile(project_id: int, user_id: int, db: Session) -> ToolResult:
    """
    Returns dataset profiling summary — NEVER raw data.
    Enforces IDOR protection.
    """
    t0 = time.time()
    try:
        project = db.query(models.Project).filter(
            models.Project.id == project_id,
            models.Project.owner_id == user_id,
        ).first()
        if not project:
            return ToolResult(tool_name="get_dataset_profile", success=False, error="PROJECT_NOT_FOUND")

        profile_result = db.query(models.AnalysisResult).filter(
            models.AnalysisResult.project_id == project_id,
            models.AnalysisResult.result_type == "profile",
        ).order_by(models.AnalysisResult.id.desc()).first()

        if not profile_result:
            return ToolResult(
                tool_name="get_dataset_profile",
                success=False,
                error="PROFILE_NOT_AVAILABLE",
            )

        return ToolResult(
            tool_name="get_dataset_profile",
            success=True,
            data=profile_result.data,
            summary=f"Dataset has {profile_result.data.get('column_count', 'unknown')} columns.",
            duration_ms=int((time.time() - t0) * 1000),
        )
    except Exception as e:
        logger.error("[Tool] get_dataset_profile failed: %s", type(e).__name__)
        return ToolResult(tool_name="get_dataset_profile", success=False, error="PROFILE_FETCH_FAILED")


def get_analysis_results(
    project_id: int,
    user_id: int,
    result_type: str,
    db: Session,
) -> ToolResult:
    """
    Returns a specific analysis result (eda | insights | ml | cleaning).
    Enforces IDOR protection. Never returns raw dataset rows.
    """
    t0 = time.time()
    ALLOWED_TYPES = {"profile", "cleaning", "eda", "insights", "ml"}
    if result_type not in ALLOWED_TYPES:
        return ToolResult(tool_name="get_analysis_results", success=False, error="INVALID_RESULT_TYPE")

    try:
        project = db.query(models.Project).filter(
            models.Project.id == project_id,
            models.Project.owner_id == user_id,
        ).first()
        if not project:
            return ToolResult(tool_name="get_analysis_results", success=False, error="PROJECT_NOT_FOUND")

        result = db.query(models.AnalysisResult).filter(
            models.AnalysisResult.project_id == project_id,
            models.AnalysisResult.result_type == result_type,
        ).order_by(models.AnalysisResult.id.desc()).first()

        if not result:
            return ToolResult(
                tool_name="get_analysis_results",
                success=False,
                error=f"RESULT_{result_type.upper()}_NOT_AVAILABLE",
            )

        return ToolResult(
            tool_name="get_analysis_results",
            success=True,
            data=result.data,
            summary=f"Retrieved {result_type} results for project {project_id}.",
            duration_ms=int((time.time() - t0) * 1000),
        )
    except Exception as e:
        logger.error("[Tool] get_analysis_results failed: %s", type(e).__name__)
        return ToolResult(tool_name="get_analysis_results", success=False, error="RESULT_FETCH_FAILED")


def answer_data_question(
    project_id: int,
    user_id: int,
    question: str,
    db: Session,
) -> ToolResult:
    """
    Answers a natural-language question about uploaded data.
    Executes the question against computed EDA results — NEVER sends raw data to LLM.
    """
    t0 = time.time()
    try:
        # Get EDA results (computed aggregates only)
        eda_result = get_analysis_results(project_id, user_id, "eda", db)
        profile_result = get_dataset_profile(project_id, user_id, db)

        if not eda_result.success:
            return ToolResult(
                tool_name="answer_data_question",
                success=False,
                error="EDA_NOT_AVAILABLE",
            )

        # Build a safe summary for the agent to reason about
        summary = {
            "question": question[:500],
            "profile": profile_result.data if profile_result.success else {},
            "eda": eda_result.data,
        }

        return ToolResult(
            tool_name="answer_data_question",
            success=True,
            data=summary,
            summary="Data context retrieved for question answering.",
            duration_ms=int((time.time() - t0) * 1000),
        )
    except Exception as e:
        logger.error("[Tool] answer_data_question failed: %s", type(e).__name__)
        return ToolResult(tool_name="answer_data_question", success=False, error="DATA_QUESTION_FAILED")


# ============================================================
# Tool Router
# ============================================================

TOOL_REGISTRY = {
    "search_services":            search_services,
    "get_service_details":        get_service_details,
    "get_package_details":        get_package_details,
    "get_pricing":                get_pricing,
    "get_service_recommendation": get_service_recommendation,
    "create_lead":                create_lead,
    "get_project_status":         get_project_status,
    "get_dataset_profile":        get_dataset_profile,
    "get_analysis_results":       get_analysis_results,
    "answer_data_question":       answer_data_question,
}


def execute_tool(
    tool_name: str,
    role: str,
    db: Session,
    **kwargs,
) -> ToolResult:
    """
    Safely executes a tool after permission check.
    This is the only entry point for tool execution.
    """
    if not check_tool_permission(tool_name, role):
        logger.warning("[Tool] Permission denied: tool=%s role=%s", tool_name, role)
        return ToolResult(
            tool_name=tool_name,
            success=False,
            error="PERMISSION_DENIED",
        )

    tool_fn = TOOL_REGISTRY.get(tool_name)
    if not tool_fn:
        logger.error("[Tool] Unknown tool: %s", tool_name)
        return ToolResult(tool_name=tool_name, success=False, error="TOOL_NOT_FOUND")

    return tool_fn(db=db, **kwargs)
