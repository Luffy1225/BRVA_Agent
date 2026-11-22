import os
from pathlib import Path

# Base paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

# Gracefully load .env if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    # Minimal fallback parser for .env
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


class Config:
    ROOT_DIR: Path = ROOT_DIR
    DATA_DIR: Path = DATA_DIR

    # LLM Provider Configuration ('auto' | 'ollama' | 'gemini' | 'offline')
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto").lower()

    # Ollama Settings (Local or LAN Server)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
    OLLAMA_TIMEOUT_SECONDS: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "30.0"))

    # Gemini Settings (Google Cloud AI)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    # Backend Connection
    BRVA_API_BASE_URL: str = os.getenv("BRVA_API_BASE_URL", "https://api.eva-virtual.com").rstrip("/")
    BRVA_AGENT_API_KEY: str = os.getenv("BRVA_AGENT_API_KEY", "")

    # Execution & Safety
    BACKEND_TIMEOUT_SECONDS: float = float(os.getenv("BACKEND_TIMEOUT_SECONDS", "5.0"))
    FALLBACK_TO_LOCAL: bool = os.getenv("FALLBACK_TO_LOCAL", "true").lower() in ("true", "1", "yes")

    # Local Data Files
    LOCAL_ROUTES_FILE: Path = DATA_DIR / "local_fallback_routes.csv"
    SAMPLE_PASS_FILE: Path = DATA_DIR / "sample_flight_pass.csv"
    SAMPLE_FAIL_FILE: Path = DATA_DIR / "sample_flight_fail.csv"

config = Config()
