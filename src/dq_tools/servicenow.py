"""ServiceNow REST client for change management.

Implemented in M2: create a change request, add a work note, attach a file.
Still to do in M6: read the change state for the deploy gate.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

import requests

from dq_tools.config import ServiceNowSettings

CHANGE_TABLE = "change_request"


class ServiceNowError(RuntimeError):
    """Raised when the ServiceNow API returns an error or an unexpected response."""


class ServiceNowClient:
    """Thin wrapper around the ServiceNow REST API."""

    def __init__(
        self,
        instance_url: str,
        username: str,
        password: str,
        session: requests.Session | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not instance_url.startswith("https://"):
            raise ValueError("instance_url must start with https://")
        self.base_url = instance_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({"Accept": "application/json"})

    @classmethod
    def from_settings(cls, settings: ServiceNowSettings) -> ServiceNowClient:
        return cls(settings.instance, settings.user, settings.password)

    def url(self, path: str) -> str:
        """Build a full API URL from a path like '/api/now/table/change_request'."""
        return f"{self.base_url}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Send a request and return the 'result' object, or raise ServiceNowError.

        Error messages include the status code and ServiceNow's error text, never the
        credentials or request headers.
        """
        kwargs.setdefault("timeout", self.timeout)
        try:
            response = self.session.request(method, self.url(path), **kwargs)
        except requests.RequestException as exc:
            raise ServiceNowError(f"{method} {path} failed: {type(exc).__name__}") from exc

        if not response.ok:
            raise ServiceNowError(
                f"{method} {path} returned {response.status_code}: {_error_text(response)}"
            )
        try:
            return response.json()["result"]
        except (ValueError, KeyError) as exc:
            raise ServiceNowError(f"{method} {path} returned an unexpected response body") from exc

    def create_change_request(
        self,
        short_description: str,
        description: str = "",
        change_type: str = "normal",
    ) -> dict:
        """Create a change request and return the created record (includes sys_id, number)."""
        payload = {
            "short_description": short_description,
            "description": description,
            "type": change_type,
        }
        return self._request("POST", f"/api/now/table/{CHANGE_TABLE}", json=payload)

    def add_work_note(self, sys_id: str, note: str) -> dict:
        """Append a work note to a change request and return the updated record."""
        return self._request(
            "PATCH",
            f"/api/now/table/{CHANGE_TABLE}/{sys_id}",
            json={"work_notes": note},
        )

    def attach_file(self, sys_id: str, file_path: str | Path) -> dict:
        """Attach a local file to a change request and return the attachment record."""
        path = Path(file_path)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with path.open("rb") as handle:
            return self._request(
                "POST",
                "/api/now/attachment/file",
                params={
                    "table_name": CHANGE_TABLE,
                    "table_sys_id": sys_id,
                    "file_name": path.name,
                },
                data=handle,
                headers={"Content-Type": content_type},
            )

    def get_change_state(self, sys_id: str) -> str:
        """TODO (M6): read the change state, used by the deploy gate."""
        raise NotImplementedError("Implement in milestone M6")


def _error_text(response: requests.Response) -> str:
    """Pull a short message out of a ServiceNow error body, falling back to the status reason."""
    try:
        error = response.json().get("error", {})
        return str(error.get("message") or error.get("detail") or response.reason)
    except ValueError:
        return str(response.reason)
