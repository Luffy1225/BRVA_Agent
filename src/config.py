import os
from pathlib import Path
from typing import Dict, Any, Optional

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


SUPPORTED_PROVIDERS = ["gemini", "ollama", "offline", "auto"]
SUPPORTED_GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
]
SUPPORTED_OLLAMA_MODELS = [
    "llama3",
    "qwen2.5",
    "mistral",
    "deepseek-r1",
]


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
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

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

    def refresh(self):
        """Reload attributes from environment variables."""
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()
        self.OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
        self.OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "30.0"))
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.BRVA_API_BASE_URL = os.getenv("BRVA_API_BASE_URL", "https://api.eva-virtual.com").rstrip("/")
        self.BRVA_AGENT_API_KEY = os.getenv("BRVA_AGENT_API_KEY", "")
        self.BACKEND_TIMEOUT_SECONDS = float(os.getenv("BACKEND_TIMEOUT_SECONDS", "5.0"))
        self.FALLBACK_TO_LOCAL = os.getenv("FALLBACK_TO_LOCAL", "true").lower() in ("true", "1", "yes")


config = Config()


def mask_secret(val: Optional[str], prefix_len: int = 4, suffix_len: int = 4) -> str:
    """Masks sensitive credentials for terminal/UI display."""
    if not val or not val.strip():
        return "(未設定 / Empty)"
    s = val.strip()
    if s in ("your_gemini_api_key_here", "brva_sk_live_your_agent_key_here"):
        return "(範例佔位符 / 未設定)"
    if len(s) <= prefix_len + suffix_len:
        return "****"
    return f"{s[:prefix_len]}...{s[-suffix_len:]}"


def update_runtime_config(updates: Dict[str, Any], persist_to_env: bool = False) -> None:
    """
    Updates runtime environment variables and config object.
    Optionally persists updates to the .env file.
    """
    for k, v in updates.items():
        val_str = str(v)
        os.environ[k] = val_str
        if hasattr(config, k):
            if isinstance(getattr(config, k), float):
                setattr(config, k, float(val_str))
            elif isinstance(getattr(config, k), bool):
                setattr(config, k, val_str.lower() in ("true", "1", "yes"))
            else:
                setattr(config, k, val_str)

    if persist_to_env:
        save_config_to_env(updates)

    # Synchronize backend client if initialized
    try:
        from src.client import backend_client
        backend_client.configure(
            base_url=config.BRVA_API_BASE_URL,
            api_key=config.BRVA_AGENT_API_KEY
        )
    except Exception:
        pass


def save_config_to_env(updates: Dict[str, Any]) -> bool:
    """
    Persists configuration parameters into the project's .env file,
    updates os.environ, and refreshes the global `config` object.
    """
    env_file = ROOT_DIR / ".env"
    existing_lines = []
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()
    elif (ROOT_DIR / ".env.example").exists():
        with open(ROOT_DIR / ".env.example", "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    updated_keys = set()
    new_lines = []
    for line in existing_lines:
        trimmed = line.strip()
        if trimmed and not trimmed.startswith("#") and "=" in trimmed:
            k, _ = trimmed.split("=", 1)
            k = k.strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}\n")
                updated_keys.add(k)
                continue
        new_lines.append(line)

    for k, v in updates.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}\n")

    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"[Config] Warning: failed to write .env file: {e}")
        return False

    update_runtime_config(updates, persist_to_env=False)
    return True
