"""
Security tests for Clarivens API:
- Security headers verification
- CORS policy enforcement
- Path traversal & secret access prevention
"""
import pytest

def test_health_check(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_security_headers_present(client):
    res = client.get("/api/v1/health")
    headers = res.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert "content-security-policy" in headers
    assert "x-request-id" in headers

def test_cors_policy(client):
    # Allowed origin
    res = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"

def test_secret_file_blocked(client):
    # Attempting to fetch .env directly must not return the file contents
    res = client.get("/.env")
    assert res.status_code in [404, 405]
    assert "AI_API_KEY" not in res.text

def test_path_traversal_blocked(client):
    res = client.get("/..%2F..%2Fetc%2Fpasswd")
    assert res.status_code in [400, 404]

def test_serve_projects_page(client):
    res = client.get("/projects.html")
    assert res.status_code == 200
    assert "Clarivens Inventory Intelligence" in res.text
    assert "VEYRA" in res.text
    assert "COVID-19" in res.text

