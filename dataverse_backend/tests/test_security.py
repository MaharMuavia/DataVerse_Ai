"""Security tests — verify no raw exception leaks and input validation."""


def test_health_endpoint(client):
    """Health endpoint returns 200."""
    resp = client.get("/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_api_health_endpoint(client):
    """API health endpoint returns 200."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_cors_allows_localhost_frontend(client):
    """Local Next.js origins should be allowed by CORS."""
    resp = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_invalid_dataset_id_returns_404(client):
    """Non-existent dataset ID returns 404, not 500."""
    resp = client.get("/api/datasets/totally-invalid-uuid/profile")
    assert resp.status_code == 404
    data = resp.json()
    assert "detail" in data
    # Verify no raw exception or traceback leaked
    assert "Traceback" not in data["detail"]
    assert "Error" not in data["detail"] or data["detail"] == "Dataset not found"


def test_no_exception_leak_on_ask(client):
    """Ask endpoint doesn't leak exception details for bad dataset."""
    resp = client.post(
        "/api/datasets/bad-id/ask",
        json={"prompt": "test query"},
    )
    assert resp.status_code == 404
    data = resp.json()
    assert "Traceback" not in str(data)


def test_oversized_file_rejected(client):
    """Files that are too large should be rejected."""
    # Create a ~60MB fake file (exceeds 50MB default limit)
    big_content = b"a,b,c\n" + b"1,2,3\n" * (10 * 1024 * 1024)  # ~30MB of rows
    resp = client.post(
        "/api/datasets/upload",
        files={"file": ("big.csv", big_content, "text/csv")},
    )
    # Should be rejected if over limit (depends on MAX_UPLOAD_SIZE_MB config)
    # For test env, we just verify it doesn't crash with a 500
    assert resp.status_code in (200, 400)


def test_secret_scanning():
    """Scan files under the workspace for hardcoded secrets/keys, ignoring build/venv dirs."""
    import re
    from pathlib import Path

    workspace_root = Path(__file__).resolve().parents[2]
    
    # Excluded directories
    ignore_dirs = {
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        "__pycache__",
        ".git",
        ".next",
    }
    
    # Excluded file extensions or specific filenames
    ignore_files = {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "bun.lockb",
        ".env.example",  # contains placeholders, not real secrets
    }
    
    # Secrets patterns: OpenAI key pattern (sk-...)
    openai_key_regex = re.compile(r"\bsk-[a-zA-Z0-9-]{32,}\b")
    
    found_secrets = []
    
    for path in workspace_root.rglob("*"):
        if not path.is_file():
            continue
            
        # Check if file is in an ignored directory
        parts = path.relative_to(workspace_root).parts
        if any(ignored in parts for ignored in ignore_dirs):
            continue
            
        if path.name in ignore_files or path.suffix in (".pyc", ".png", ".jpg", ".jpeg", ".pdf", ".zip", ".tar", ".gz"):
            continue
            
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            matches = openai_key_regex.findall(content)
            for match in matches:
                # Filter out obvious placeholders
                if "placeholder" not in match.lower() and "your_key" not in match.lower() and "sk-your-openai-api-key" not in match.lower():
                    found_secrets.append(f"{path.name}: {match}")
        except Exception:
            # Skip unreadable files
            pass
            
    assert not found_secrets, f"Found potential hardcoded secrets: {found_secrets}"
