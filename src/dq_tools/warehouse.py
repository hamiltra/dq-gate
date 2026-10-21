"""Snowflake connection helper (key-pair auth). Needs the optional 'snowflake' extra."""

from __future__ import annotations

import os

from dq_tools.config import SnowflakeSettings


def connect(settings: SnowflakeSettings):
    """Open a Snowflake connection using the service user's private key file."""
    import snowflake.connector  # imported lazily so unit tests do not need the connector

    return snowflake.connector.connect(
        account=settings.account,
        user=settings.user,
        role=settings.role,
        warehouse=settings.warehouse,
        database=settings.database,
        private_key_file=os.path.expanduser(settings.private_key_path),
    )
