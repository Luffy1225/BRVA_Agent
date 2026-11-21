import requests
from typing import Optional, Dict, Any
from src.config import config

class BackendClient:
    """
    HTTP Client communicating with the BRVA Production / Staging Backend API.
    Handles x-agent-key authentication, timeouts, and graceful error handling.
    """
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or config.BRVA_API_BASE_URL).rstrip("/")
        self.api_key = api_key or config.BRVA_AGENT_API_KEY
        self.timeout = config.BACKEND_TIMEOUT_SECONDS

    def _headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": "BRVA-Agent/1.0",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["x-agent-key"] = self.api_key
        return headers

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 503:
                print(f"[BackendClient] ⚠️ Server returned 503 (Agent disabled by administrator).")
            else:
                print(f"[BackendClient] Warning: {url} returned HTTP {resp.status_code}: {resp.text[:100]}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[BackendClient] ⚠️ Network error reaching {url}: {e}")
            return None

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            resp = requests.post(url, headers=self._headers(), json=json_data, timeout=self.timeout)
            if resp.status_code in (200, 201):
                return resp.json()
            else:
                print(f"[BackendClient] Warning: {url} POST returned HTTP {resp.status_code}: {resp.text[:100]}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[BackendClient] ⚠️ Network error posting to {url}: {e}")
            return None

backend_client = BackendClient()
