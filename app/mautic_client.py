import os
import json
import time
from typing import Any, Dict
from urllib.parse import urljoin

import requests

from app.exceptions import MauticAuthError, MauticConnectionError, MauticAPIError


class MauticClient:
    def __init__(self, base_url: str, token_file: str, timeout_seconds: int = 30):
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.token_file = token_file
        self.timeout_seconds = timeout_seconds

        self.client_id = os.getenv("MAUTIC_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("MAUTIC_CLIENT_SECRET", "").strip()
        if not self.client_id or not self.client_secret:
            raise MauticAuthError("Missing MAUTIC_CLIENT_ID / MAUTIC_CLIENT_SECRET env vars")

        self.session = requests.Session()
        self.token_data: Dict[str, Any] = {}
        self._load_tokens()

    # ------------------------
    # Token persistence
    # ------------------------
    def _load_tokens(self) -> None:
        try:
            with open(self.token_file, "r", encoding="utf-8") as f:
                self.token_data = json.load(f)
        except FileNotFoundError:
            self.token_data = {}
        except Exception:
            # if corrupt, start fresh
            self.token_data = {}

    def _save_tokens(self, token_response: Dict[str, Any]) -> None:
        expires_in = token_response.get("expires_in")
        if expires_in is not None:
            try:
                token_response["expires_at"] = time.time() + int(expires_in)
            except Exception:
                token_response["expires_at"] = time.time() + 300  # fallback

        self.token_data.update(token_response)

        os.makedirs(os.path.dirname(self.token_file), exist_ok=True) # Ensure directory exists
        with open(self.token_file, "w", encoding="utf-8") as f:
            json.dump(self.token_data, f, indent=2)

    # ------------------------
    # Client Credentials flow
    # ------------------------
    def fetch_client_credentials_token(self) -> str:
        token_url = urljoin(self.base_url, "oauth/v2/token")
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        try:
            resp = self.session.post(token_url, data=payload, timeout=self.timeout_seconds)
        except requests.RequestException as e:
            raise MauticConnectionError(f"Token request failed: {e}") from e

        if resp.status_code != 200:
            raise MauticAuthError(f"Token endpoint error: {resp.status_code} body={resp.text}")

        try:
            data = resp.json()
        except ValueError as e:
            raise MauticAuthError(f"Token response not JSON: {resp.text}") from e

        if not data.get("access_token"):
            raise MauticAuthError(f"Token response missing access_token: {data}")

        self._save_tokens(data)
        return str(data["access_token"])

    def get_valid_access_token(self) -> str:
        access_token = self.token_data.get("access_token")
        expires_at = float(self.token_data.get("expires_at") or 0)

        # 60-second buffer
        if access_token and time.time() < (expires_at - 60):
            return str(access_token)

        return self.fetch_client_credentials_token()

    # ------------------------
    # Requests
    # ------------------------
    def request_json(self, method: str, endpoint: str, *, json_body=None, params=None) -> Dict[str, Any]:
        url = urljoin(self.base_url, endpoint.lstrip("/"))

        def do_request(token: str) -> requests.Response:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            return self.session.request(
                method=method.upper(),
                url=url,
                json=json_body,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )

        # first try
        token = self.get_valid_access_token()
        try:
            resp = do_request(token)
        except requests.RequestException as e:
            raise MauticConnectionError(f"Request failed: {e}") from e

        # if 401, token might be revoked; fetch a new one and retry once
        if resp.status_code == 401:
            token = self.fetch_client_credentials_token()
            try:
                resp = do_request(token)
            except requests.RequestException as e:
                raise MauticConnectionError(f"Retry failed: {e}") from e

        if resp.status_code in (401, 403):
            raise MauticAuthError(f"Auth failed: {resp.status_code} body={resp.text}")

        if resp.status_code >= 400:
            raise MauticAPIError(
                f"Mautic API error: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        try:
            return resp.json()
        except ValueError as e:
            raise MauticAPIError("Response not JSON", status_code=resp.status_code, response_body=resp.text) from e