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


@dataclass(frozen=True)
class SnowflakeSettings:
    account: str
    user: str
    role: str
    warehouse: str
    database: str
    private_key_path: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> SnowflakeSettings:
        env = os.environ if env is None else env
        names = (
            "SNOWFLAKE_ACCOUNT",
            "SNOWFLAKE_USER",
            "SNOWFLAKE_ROLE",
            "SNOWFLAKE_WAREHOUSE",
            "SNOWFLAKE_DATABASE",
            "SNOWFLAKE_PRIVATE_KEY_PATH",
        )
        missing = [name for name in names if not env.get(name)]
        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")
        return cls(
            account=env["SNOWFLAKE_ACCOUNT"],
            user=env["SNOWFLAKE_USER"],
            role=env["SNOWFLAKE_ROLE"],
            warehouse=env["SNOWFLAKE_WAREHOUSE"],
            database=env["SNOWFLAKE_DATABASE"],
            private_key_path=env["SNOWFLAKE_PRIVATE_KEY_PATH"],
        )
