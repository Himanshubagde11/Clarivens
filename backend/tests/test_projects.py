"""
Project CRUD and IDOR authorization tests for Clarivens API.
"""
import pytest
from backend.database import models

def test_create_project(client):
    res = client.post("/api/v1/projects", json={"name": "Sales Forecast Q3"})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Sales Forecast Q3"
    assert data["id"] is not None
    assert data["status"] == "created"

def test_project_invalid_name(client):
    # Empty name
    res = client.post("/api/v1/projects", json={"name": ""})
    assert res.status_code == 422

def test_idor_protection(client, db_session):
    # Create a project owned by user 2
    proj_u2 = models.Project(id=999, name="Private User 2 Project", owner_id=2, status="created")
    db_session.add(proj_u2)
    db_session.commit()

    # The default dev user is user 1. Attempting to access project 999 must return 404
    res = client.get("/api/v1/projects/999")
    assert res.status_code == 404
    body = res.json()
    assert "not found" in str(body).lower() or body.get("error", {}).get("code") == "PROJECT_NOT_FOUND"
