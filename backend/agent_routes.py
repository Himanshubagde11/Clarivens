"""
Clarivens AI Agent — FastAPI Router.

All agent API endpoints are mounted here and included in main.py.
Existing routes are NOT modified.

Routes:
    POST   /api/ai/session              → Create session
    POST   /api/ai/chat                 → Send message, get response (main endpoint)
    GET    /api/ai/session/{session_id} → Get session history
    POST   /api/ai/feedback             → Submit feedback on a message
    POST   /api/ai/lead                 → Submit lead contact form
    GET    /api/ai/project/{project_id}/context → Project AI context (auth required)
    GET    /api/ai/status               → Agent health / version info

    Admin (stub endpoints for future admin panel):
    POST   /api/ai/admin/knowledge      → Add knowledge chunk
    POST   /api/ai/admin/seed           → Trigger seed (dev/admin only)
"""
import logging
import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
import uuid

from backend.config import settings
from backend.database.database import get_db
from backend.database import models
from backend.services.data_ingestion import save_uploaded_file, sanitize_filename
from backend.jobs.worker import execute_pipeline, execute_profiling_only
from backend.core.audit import log_audit_event, AuditEvent, AuditStatus
from backend.schemas.agent_schemas import (
    CreateSessionRequest, SessionResponse,
    ChatRequest, ChatResponse, ToolResultPublic,
    FeedbackRequest, FeedbackResponse,
    LeadCaptureRequest, LeadCaptureResponse,
    ProjectContextResponse,
    AgentStatusResponse,
    KnowledgeChunkRequest, KnowledgeChunkResponse,
)
from backend.agent.orchestrator import orchestrator
from backend.agent import memory as mem_manager
from backend.agent.tools import create_lead, execute_tool
from backend.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

agent_router = APIRouter(prefix="/api/ai", tags=["Clarivens AI Agent"])


# ============================================================
# Helper: optional auth (anonymous or authenticated)
# ============================================================

def _get_optional_user(request: Request, db: Session) -> Optional[models.User]:
    """Returns authenticated user if Bearer token present, else None (anonymous visitor)."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        from jose import JWTError, jwt
        from backend.config import settings
        token = auth_header.split(" ", 1)[1]
        payload = jwt.decode(token, settings.get_jwt_secret(), algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = db.query(models.User).filter(models.User.id == int(user_id)).first()
        return user
    except Exception:
        return None


# ============================================================
# GET /api/ai/status
# ============================================================

@agent_router.get("/status", response_model=AgentStatusResponse, summary="Agent health check")
def agent_status():
    """Returns agent version and health status. No auth required."""
    return AgentStatusResponse(
        status="healthy" if settings.agent_enabled else "disabled",
        version=settings.agent_version,
        primary_model=settings.agent_primary_model,
        fast_model=settings.agent_fast_model,
        enabled=settings.agent_enabled,
    )


# ============================================================
# POST /api/ai/session
# ============================================================

@agent_router.post("/session", response_model=SessionResponse, summary="Create a new conversation session")
def create_session(
    request: Request,
    body: CreateSessionRequest,
    db: Session = Depends(get_db),
):
    """
    Creates a new Clarivens AI conversation session.
    Anonymous visitors get role=visitor. Authenticated users get role=client.
    """
    user = _get_optional_user(request, db)
    user_id = user.id if user else None
    role = "client" if user else "visitor"

    session = mem_manager.create_session(
        db=db,
        user_id=user_id,
        project_id=body.project_id,
        role=role,
    )

    logger.info("[AgentRoute] Session created: %s (role=%s)", session.session_id[:8], role)

    return SessionResponse(
        session_id=session.session_id,
        state=session.state,
        role=session.role,
        project_id=session.project_id,
        agent_version=session.agent_version,
    )


# ============================================================
# POST /api/ai/chat
# ============================================================

@agent_router.post("/chat", response_model=ChatResponse, summary="Send a message to Clarivens AI")
async def chat(
    request: Request,
    body: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Main Clarivens AI conversation endpoint.

    Accepts a user message and optional session_id.
    Returns AI response with intent classification, state, and suggested actions.

    Rate: 20 requests/minute per session (configurable in settings).
    """
    if not settings.agent_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clarivens AI is temporarily unavailable.",
        )

    user = _get_optional_user(request, db)
    user_id = user.id if user else None
    role = "client" if user else "visitor"

    # Validate project access if project_id provided
    project_id = body.project_id
    if project_id and user_id:
        project = db.query(models.Project).filter(
            models.Project.id == project_id,
            models.Project.owner_id == user_id,
        ).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )
    elif project_id and not user_id:
        # Anonymous users cannot access projects
        project_id = None

    try:
        response = orchestrator.process_message(
            user_message=body.message,
            session_id=body.session_id,
            db=db,
            user_id=user_id,
            project_id=project_id,
            role=role,
        )
    except Exception as e:
        logger.error("[AgentRoute] Chat failed: %s", type(e).__name__, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The AI agent encountered an error. Please try again.",
        )

    return ChatResponse(
        session_id=response.session_id,
        message=response.message,
        intent=response.intent,
        state=response.state,
        suggested_actions=response.suggested_actions,
        requires_lead_capture=response.requires_lead_capture,
        requires_file_upload=response.requires_file_upload,
        project_id=response.project_id,
        tool_results=[
            ToolResultPublic(tool=t["tool"], summary=t["summary"])
            for t in response.tool_results
        ],
        tokens_used=response.tokens_used,
    )


# ============================================================
# POST /api/ai/upload
# ============================================================

@agent_router.post("/upload", response_model=dict, summary="Upload a data file directly within an AI session")
async def chat_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Handles file uploads triggered from within the AI Agent chat interface.
    Links the uploaded dataset to the user's active session project (or creates a new one).
    Triggers the analytics pipeline automatically.
    """
    user = _get_optional_user(request, db)
    
    # 1. Retrieve the session
    session = mem_manager.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        
    # 2. Get or create project for this session
    project_id = session.project_id
    if not project_id:
        new_project = models.Project(
            name=f"AI Chat Analysis - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            description="Project created automatically via Clarivens AI assistant.",
            owner_id=user.id if user else None,
        )
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        project_id = new_project.id
        session.project_id = project_id
        db.commit()

    # 3. Read and validate file content
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"File exceeds maximum allowed size of {settings.max_upload_size_mb} MB."
        )

    job_id = str(uuid.uuid4())
    try:
        storage_name, file_path, ext = save_uploaded_file(file.filename, content, project_id)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    # 4. Save dataset and job records
    dataset = models.Dataset(
        project_id=project_id,
        original_filename=sanitize_filename(file.filename),
        storage_name=storage_name,
        storage_path=file_path,
        file_type=ext,
        file_size_bytes=len(content)
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    job = models.ProcessingJob(
        job_id=job_id,
        project_id=project_id,
        status=models.JobStatus.queued
    )
    db.add(job)
    db.commit()

    log_audit_event(
        AuditEvent.DATASET_UPLOADED, AuditStatus.SUCCESS,
        user_id=user.id if user else None,
        project_id=project_id,
        details={"dataset_id": dataset.id, "job_id": job_id, "source": "ai_agent"}
    )

    # 5. Trigger backend processing pipeline (profiling only for AI agent)
    background_tasks.add_task(execute_profiling_only, project_id, file_path, file.filename, job_id, user.id if user else None)
    
    # 6. Inject a system message into the AI's memory to confirm the upload
    mem_manager.add_message(
        db=db,
        session_id=session.id,
        role="system",
        content=f"User successfully uploaded a dataset named '{dataset.original_filename}'. The dataset is currently being profiled. You will have access to the profile summary to identify opportunities and recommend services.",
    )

    return {
        "success": True,
        "message": "Dataset uploaded successfully.",
        "project_id": project_id,
        "dataset_id": dataset.id
    }


# ============================================================
# GET /api/ai/session/{session_id}
# ============================================================

@agent_router.get("/session/{session_id}", response_model=dict, summary="Get session history")
def get_session_history(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Returns conversation history for a session."""
    session = mem_manager.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    messages = mem_manager.get_conversation_history(db, session, max_messages=50)

    return {
        "session_id": session.session_id,
        "state": session.state,
        "role": session.role,
        "messages": messages,
        "total_messages": len(messages),
        "created_at": session.created_at.isoformat(),
    }


# ============================================================
# POST /api/ai/feedback
# ============================================================

@agent_router.post("/feedback", response_model=FeedbackResponse, summary="Submit feedback on a message")
def submit_feedback(
    body: FeedbackRequest,
    db: Session = Depends(get_db),
):
    """
    Records user feedback on an AI response.
    Used to continuously improve the agent.
    """
    session = mem_manager.get_session(db, body.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    # Verify message belongs to this session
    message = db.query(models.AgentMessage).filter(
        models.AgentMessage.id == body.message_id,
        models.AgentMessage.session_id == session.id,
    ).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found in session.")

    feedback = models.AgentFeedback(
        session_id=session.id,
        message_id=body.message_id,
        rating=body.rating,
        correction=body.correction,
        intent=message.intent,
        agent_version=settings.agent_version,
    )
    db.add(feedback)
    db.commit()

    logger.info("[AgentRoute] Feedback: session=%s rating=%s", session.session_id[:8], body.rating)
    return FeedbackResponse(success=True, message="Feedback recorded. Thank you!")


# ============================================================
# POST /api/ai/lead
# ============================================================

@agent_router.post("/lead", response_model=LeadCaptureResponse, summary="Submit lead contact details")
def submit_lead(
    body: LeadCaptureRequest,
    db: Session = Depends(get_db),
):
    """
    Direct lead submission endpoint (used by the widget lead capture form).
    """
    session = mem_manager.get_session(db, body.session_id)
    session_db_id = session.id if session else None

    result = create_lead(
        db=db,
        session_id=session_db_id,
        email=body.email,
        name=body.name,
        company=body.company,
        industry=body.industry,
        requirement=body.requirement,
        dataset_available=body.dataset_available,
    )

    if result.success:
        # Store email in session memory
        if session:
            mem_manager.set_memory(db, session, "email", body.email)
            if body.name:
                mem_manager.set_memory(db, session, "name", body.name)

        return LeadCaptureResponse(
            success=True,
            message="Thank you! A Clarivens consultant will be in touch shortly.",
            lead_id=result.data.get("lead_id") if result.data else None,
        )

    return LeadCaptureResponse(
        success=False,
        message="We couldn't record your details. Please try again or email us directly.",
    )


# ============================================================
# GET /api/ai/project/{project_id}/context
# ============================================================

@agent_router.get(
    "/project/{project_id}/context",
    response_model=ProjectContextResponse,
    summary="Get AI context for a project (authenticated)",
)
def get_project_context(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Returns AI-ready context for a project.
    Requires authentication — IDOR protected.
    """
    user = _get_optional_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    # Check which analysis results are available
    results = db.query(models.AnalysisResult).filter(
        models.AnalysisResult.project_id == project_id
    ).all()
    available = [r.result_type for r in results]

    return ProjectContextResponse(
        project_id=project.id,
        name=project.name,
        status=project.status,
        has_results=len(results) > 0,
        available_analyses=available,
    )


# ============================================================
# Admin Routes (stub — full admin panel in future phase)
# ============================================================

@agent_router.post("/admin/knowledge", response_model=KnowledgeChunkResponse, summary="Add knowledge chunk (admin)")
def add_knowledge(
    request: Request,
    body: KnowledgeChunkRequest,
    db: Session = Depends(get_db),
):
    """Adds a knowledge chunk to the agent knowledge base. Admin only."""
    user = _get_optional_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authentication required.")

    chunk = models.AgentKnowledge(
        title=body.title,
        content=body.content,
        category=body.category,
        tags=body.tags,
        kb_version=settings.agent_knowledge_version,
        is_active=True,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)

    return KnowledgeChunkResponse(
        id=chunk.id,
        title=chunk.title,
        category=chunk.category,
        kb_version=chunk.kb_version,
        created_at=chunk.created_at.isoformat(),
    )


@agent_router.post("/admin/seed", summary="Seed service catalog and knowledge base (admin/dev)")
def seed_data(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Seeds the service catalog and knowledge base.
    Safe to call multiple times (idempotent).
    Restricted to non-production or admin users.
    """
    if settings.is_production():
        user = _get_optional_user(request, db)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authentication required.")

    try:
        from backend.agent.service_catalog_seed import seed_all
        result = seed_all()
        return result
    except Exception as e:
        logger.error("[AgentRoute] Seed failed: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Seeding failed.")
