from pathlib import Path


def test_config_enforces_secret_loader():
    content = Path("crypto_agent/config.py").read_text()
    assert "def _require_secret" in content
    assert "DASHBOARD_PASSWORD = _require_secret(\"DASHBOARD_PASSWORD\")" in content
    assert "DB_PASSWORD = _require_secret(\"DB_PASSWORD\")" in content


def test_config_has_cors_allowlist_setting():
    content = Path("crypto_agent/config.py").read_text()
    assert "CORS_ORIGINS = _csv_env" in content


def test_api_and_dashboard_use_configured_cors_origins():
    api_content = Path("crypto_agent/api/server.py").read_text()
    dashboard_content = Path("crypto_agent/dashboard/app.py").read_text()
    assert "allow_origins=config.CORS_ORIGINS" in api_content
    assert "allow_origins=config.CORS_ORIGINS" in dashboard_content


def test_env_production_template_exists():
    template = Path(".env.production.example")
    assert template.exists()
    content = template.read_text()
    assert "APP_ENV=production" in content
    assert "CORS_ORIGINS=" in content
