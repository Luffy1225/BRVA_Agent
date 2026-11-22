import requests
from typing import Optional, Dict, Any
from src.config import config, clean_api_url

class BackendClient:
    """
    HTTP Client communicating with the BRVA Production / Staging Backend API.
    Handles x-agent-key authentication, user delegation tokens, timeouts, and graceful error handling.
    """
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = clean_api_url(base_url or config.BRVA_API_BASE_URL)
        self.api_key = api_key if api_key is not None else config.BRVA_AGENT_API_KEY
        self.timeout = config.BACKEND_TIMEOUT_SECONDS

    def _headers(self, user_token: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "User-Agent": "BRVA-Agent/1.0",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["x-agent-key"] = self.api_key
        if user_token:
            headers["Authorization"] = f"Bearer {user_token}"
        return headers

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, user_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            resp = requests.get(url, headers=self._headers(user_token=user_token), params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 503:
                print(f"[BackendClient] ⚠️ Server returned 503 (Agent disabled by administrator).")
            else:
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        data["_status_code"] = resp.status_code
                        return data
                except Exception:
                    pass
                print(f"[BackendClient] Warning: {url} returned HTTP {resp.status_code}: {resp.text[:100]}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[BackendClient] ⚠️ Network error reaching {url}: {e}")
            return None

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, user_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            resp = requests.post(url, headers=self._headers(user_token=user_token), json=json_data, timeout=self.timeout)
            if resp.status_code in (200, 201):
                return resp.json()
            else:
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        data["_status_code"] = resp.status_code
                        return data
                    return {"data": data, "_status_code": resp.status_code}
                except Exception:
                    print(f"[BackendClient] Warning: {url} POST returned HTTP {resp.status_code}: {resp.text[:100]}")
                    return {"error": resp.text[:100], "_status_code": resp.status_code}
        except requests.exceptions.RequestException as e:
            print(f"[BackendClient] ⚠️ Network error posting to {url}: {e}")
            return None

    def configure(self, base_url: Optional[str] = None, api_key: Optional[str] = None, timeout: Optional[float] = None):
        """Dynamically reconfigures the client's connection parameters."""
        if base_url is not None:
            self.base_url = clean_api_url(base_url)
        if api_key is not None:
            self.api_key = api_key
        if timeout is not None:
            self.timeout = timeout

    def test_connection(self) -> tuple[bool, str]:
        """
        Tests connectivity to the BRVA backend using current base_url and api_key.
        Returns (is_success, status_description).
        """
        try:
            url = f"{self.base_url}/api/routes"
            resp = requests.get(url, headers=self._headers(), timeout=min(self.timeout, 4.0))
            if resp.status_code == 200:
                return True, f"連線正常 (HTTP 200, {self.base_url})"
            elif resp.status_code == 401:
                return False, "金鑰無效或授權失敗 (HTTP 401: Invalid Agent Key)"
            elif resp.status_code == 403:
                return False, "存取被拒 (HTTP 403: Forbidden)"
            elif resp.status_code == 429:
                return False, "請求過於頻繁 (HTTP 429: Rate Limited)"
            elif resp.status_code == 503:
                return False, "管理員已暫停 Agent 存取 (HTTP 503 Killswitch)"
            else:
                return True, f"伺服器在線 (HTTP {resp.status_code})"
        except requests.exceptions.RequestException as e:
            return False, f"無法連線伺服器 ({str(e)[:60]})"

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validates a delegation token or user access token against the backend.
        Returns pilot profile if valid, None otherwise.
        """
        clean_token = (token or "").strip()
        if not clean_token:
            return None
        return self.get("/api/agent/token", user_token=clean_token)

backend_client = BackendClient()
