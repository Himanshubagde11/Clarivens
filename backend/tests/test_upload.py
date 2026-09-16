"""
File upload and validation tests for Clarivens API.
"""
import io
import pytest

def test_upload_valid_csv(client):
    # First create a project
    p_res = client.post("/api/v1/projects", json={"name": "Upload Test Project"})
    project_id = p_res.json()["id"]

    csv_data = b"id,sales,region\n1,100,North\n2,200,South\n3,300,East\n"
    res = client.post(
        f"/api/v1/projects/{project_id}/upload",
        files={"file": ("test_sales.csv", io.BytesIO(csv_data), "text/csv")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] is not None
    assert data["job_id"] is not None
    assert data["status"] == "queued"

def test_upload_invalid_extension(client):
    p_res = client.post("/api/v1/projects", json={"name": "Upload Malicious Test"})
    project_id = p_res.json()["id"]

    malicious_script = b"print('malicious code')"
    res = client.post(
        f"/api/v1/projects/{project_id}/upload",
        files={"file": ("malicious.py", io.BytesIO(malicious_script), "text/x-python")}
    )
    assert res.status_code == 400
    body = res.json()
    assert "extension" in str(body).lower() or "not allowed" in str(body).lower() or "file type" in str(body).lower()
