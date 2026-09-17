"""
Asynchronous pipeline worker for Clarivens.
Orchestrates data ingestion, cleaning, EDA, AI insights, and ML predictive modeling.
Can be run in-process or as a standalone Azure Container Apps Job.
"""
import os
import sys
import logging
from typing import Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database import models
from backend.core.audit import log_audit_event, AuditEvent, AuditStatus
from backend.services.data_ingestion import analyze_dataset_profile
from backend.services.analytics_engine import run_data_cleaning, run_eda
from backend.services.ml_engine import run_predictive_modeling
from backend.services.ai_engine import generate_insights

logger = logging.getLogger(__name__)

def execute_pipeline(project_id: int, file_path: str, filename: str, job_id: str = None, user_id: int = None, org_id: int = None) -> bool:
    """
    Executes the end-to-end analytics workflow and persists structured results.
    Never exposes raw unhandled exceptions.
    """
    db: Session = SessionLocal()
    try:
        # Retrieve project
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not project:
            logger.error(f"[Worker] Project {project_id} not found.")
            return False

        project.status = "processing"
        db.commit()

        # Find or create processing job
        job = None
        if job_id:
            job = db.query(models.ProcessingJob).filter(models.ProcessingJob.job_id == job_id).first()
        if not job:
            job = models.ProcessingJob(
                project_id=project_id,
                job_id=job_id,
                job_type="full_pipeline",
                status="running"
            )
            db.add(job)
            db.commit()
            db.refresh(job)
        else:
            job.status = "running"
            db.commit()

        # Audit start
        log_audit_event(
            event=AuditEvent.ANALYSIS_STARTED,
            status=AuditStatus.SUCCESS,
            user_id=user_id or project.owner_id,
            org_id=org_id or getattr(project, "organization_id", None),
            resource_type="project",
            resource_id=str(project_id),
            metadata={"filename": filename}
        )

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        # Step 1: Profiling
        logger.info(f"[Worker] Profiling dataset for project {project_id}")
        profile = analyze_dataset_profile(file_path, filename)
        db.add(models.AnalysisResult(project_id=project_id, result_type="profile", data=profile))
        db.commit()

        # Step 2: Data Cleaning
        logger.info(f"[Worker] Cleaning dataset for project {project_id}")
        clean_result = run_data_cleaning(file_path, ext)
        db.add(models.AnalysisResult(project_id=project_id, result_type="cleaning", data=clean_result))
        db.commit()

        # Step 3: EDA & Visual Analysis
        eda_target_path = clean_result.get("cleaned_file_path") or file_path
        logger.info(f"[Worker] Running exploratory data analysis for project {project_id}")
        eda_result = run_eda(eda_target_path, ext)
        db.add(models.AnalysisResult(project_id=project_id, result_type="eda", data=eda_result))
        db.commit()

        # Step 4: AI Insights
        logger.info(f"[Worker] Generating AI business insights for project {project_id}")
        insights = generate_insights(profile, eda_result)
        db.add(models.AnalysisResult(project_id=project_id, result_type="insights", data=insights))
        db.commit()

        # Step 5: Predictive Modeling (AutoML with smart target selection)
        logger.info(f"[Worker] Evaluating ML predictive modeling for project {project_id}")
        ml_result = run_predictive_modeling(eda_target_path, ext)
        db.add(models.AnalysisResult(project_id=project_id, result_type="ml", data=ml_result))
        db.commit()

        # Complete pipeline
        job.status = "completed"
        project.status = "completed"
        db.commit()

        log_audit_event(
            event=AuditEvent.ANALYSIS_COMPLETED,
            status=AuditStatus.SUCCESS,
            user_id=user_id or project.owner_id,
            org_id=org_id or getattr(project, "organization_id", None),
            resource_type="project",
            resource_id=str(project_id)
        )
        logger.info(f"[Worker] Successfully completed pipeline for project {project_id}")
        return True

    except Exception as exc:
        db.rollback()
        err_str = str(exc)
        logger.error(f"[Worker] Pipeline execution failed for project {project_id}: {err_str}", exc_info=True)

        if 'job' in locals() and job:
            job.status = "failed"
            job.error_message = "Analysis failed during automated processing."
        if 'project' in locals() and project:
            project.status = "failed"
        db.commit()

        log_audit_event(
            event=AuditEvent.ANALYSIS_FAILED,
            status=AuditStatus.FAILURE,
            user_id=user_id or (project.owner_id if 'project' in locals() and project else None),
            org_id=org_id or (getattr(project, "organization_id", None) if 'project' in locals() and project else None),
            resource_type="project",
            resource_id=str(project_id),
            error_message="Pipeline execution error"
        )
        return False
    finally:
        db.close()


def execute_profiling_only(project_id: int, file_path: str, filename: str, job_id: str = None, user_id: int = None, org_id: int = None) -> bool:
    """
    Executes only the profiling step for AI agent data uploads.
    Does not run EDA, ML, or insights to save compute and avoid giving away free analysis.
    """
    db: Session = SessionLocal()
    try:
        # Retrieve project
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not project:
            logger.error(f"[Worker] Project {project_id} not found.")
            return False

        project.status = "profiling"
        db.commit()

        # Find or create processing job
        job = None
        if job_id:
            job = db.query(models.ProcessingJob).filter(models.ProcessingJob.job_id == job_id).first()
        if not job:
            job = models.ProcessingJob(
                project_id=project_id,
                job_id=job_id,
                job_type="profiling_only",
                status="running"
            )
            db.add(job)
            db.commit()
            db.refresh(job)
        else:
            job.status = "running"
            db.commit()

        # Audit start
        log_audit_event(
            event=AuditEvent.ANALYSIS_STARTED,
            status=AuditStatus.SUCCESS,
            user_id=user_id or project.owner_id,
            org_id=org_id or getattr(project, "organization_id", None),
            resource_type="project",
            resource_id=str(project_id),
            metadata={"filename": filename, "mode": "profiling_only"}
        )

        # Step 1: Profiling
        logger.info(f"[Worker] Profiling dataset for project {project_id}")
        profile = analyze_dataset_profile(file_path, filename)
        db.add(models.AnalysisResult(project_id=project_id, result_type="profile", data=profile))
        db.commit()

        # Complete pipeline
        job.status = "completed"
        project.status = "completed"
        db.commit()

        log_audit_event(
            event=AuditEvent.ANALYSIS_COMPLETED,
            status=AuditStatus.SUCCESS,
            user_id=user_id or project.owner_id,
            org_id=org_id or getattr(project, "organization_id", None),
            resource_type="project",
            resource_id=str(project_id)
        )
        logger.info(f"[Worker] Successfully completed profiling for project {project_id}")
        return True

    except Exception as exc:
        db.rollback()
        err_str = str(exc)
        logger.error(f"[Worker] Profiling execution failed for project {project_id}: {err_str}", exc_info=True)

        if 'job' in locals() and job:
            job.status = "failed"
            job.error_message = "Profiling failed."
        if 'project' in locals() and project:
            project.status = "failed"
        db.commit()

        log_audit_event(
            event=AuditEvent.ANALYSIS_FAILED,
            status=AuditStatus.FAILURE,
            user_id=user_id or (project.owner_id if 'project' in locals() and project else None),
            org_id=org_id or (getattr(project, "organization_id", None) if 'project' in locals() and project else None),
            resource_type="project",
            resource_id=str(project_id),
            error_message="Profiling execution error"
        )
        return False
    finally:
        db.close()


if __name__ == "__main__":
    # Can be invoked directly as a standalone CLI worker
    print("[Worker] Clarivens Analytics Worker CLI ready.")
