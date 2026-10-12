"""ServiceNow client skeleton (milestone M2).

Only construction and URL handling are implemented so far. The change-management calls
are stubbed with clear TODOs so M2 starts from a tested base.
"""

from __future__ import annotations

import requests

from dq_tools.config import ServiceNowSettings


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

    # --- M2: implement below -------------------------------------------------

    def create_change_request(self, short_description: str, description: str = "") -> dict:
        """TODO (M2): POST /api/now/table/change_request and return the created record."""
        raise NotImplementedError("Implement in milestone M2")

    def add_work_note(self, sys_id: str, note: str) -> dict:
        """TODO (M2): PATCH the change request with a work note."""
        raise NotImplementedError("Implement in milestone M2")

    def attach_file(self, sys_id: str, file_path: str) -> dict:
        """TODO (M2): POST /api/now/attachment/file?table_name=change_request&table_sys_id=..."""
        raise NotImplementedError("Implement in milestone M2")

    def get_change_state(self, sys_id: str) -> str:
        """TODO (M6): read the change state, used by the deploy gate."""
        raise NotImplementedError("Implement in milestone M6")
