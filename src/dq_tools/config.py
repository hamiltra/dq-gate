"""Environment-based configuration. Secrets come from env vars, never from the repo."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


@dataclass(frozen=True)
class ServiceNowSettings:
    instance: str
    user: str
    password: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ServiceNowSettings:
        env = os.environ if env is None else env
        missing = [
            name
            for name in ("SERVICENOW_INSTANCE", "SERVICENOW_USER", "SERVICENOW_PASSWORD")
            if not env.get(name)
        ]
        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")
        return cls(
            instance=env["SERVICENOW_INSTANCE"],
            user=env["SERVICENOW_USER"],
            password=env["SERVICENOW_PASSWORD"],
        )
