import tomllib
from pathlib import Path

from engine.config import KNOWN_KEYS

ROOT = Path(__file__).parents[1]


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_streamlit_config_is_hardened():
    cfg = tomllib.loads(read(".streamlit/config.toml"))
    assert cfg["server"]["enableXsrfProtection"] is True
    assert cfg["server"]["maxUploadSize"] == 1
    assert cfg["browser"]["gatherUsageStats"] is False
    assert cfg["client"]["showErrorDetails"] is False
    assert "enableCORS" not in cfg["server"]  # default (aan) laten; uitzetten botst met XSRF


def test_dockerfile_runs_as_non_root_and_bakes_no_secrets():
    df = read("Dockerfile")
    assert "USER app" in df
    assert "HEALTHCHECK" in df
    assert "${PORT}" in df
    assert "secrets.toml" not in df
    assert "COPY .env" not in df and "COPY . ." not in df  # alleen expliciete mappen, nooit de hele context


def test_dockerignore_excludes_secrets():
    ignored = read(".dockerignore").splitlines()
    for entry in (".env", ".streamlit/secrets.toml", ".git", ".venv"):
        assert entry in ignored


def test_env_example_documents_all_keys_without_values():
    lines = [line for line in read(".env.example").splitlines() if line and not line.startswith("#")]
    documented = {line.split("=")[0].lstrip("# ") for line in read(".env.example").splitlines() if "=" in line}
    assert set(KNOWN_KEYS) - {"GOOGLE_API_KEY"} <= documented
    assert all(line.endswith("=") for line in lines if line.startswith("GEMINI_API_KEY"))


def test_gitignore_excludes_secrets():
    ignored = read(".gitignore").splitlines()
    assert ".env" in ignored and ".streamlit/secrets.toml" in ignored
