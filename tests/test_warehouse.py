import sys
import types

from dq_tools.config import SnowflakeSettings
from dq_tools.warehouse import connect


def test_connect_passes_key_pair_settings_to_the_connector(monkeypatch):
    captured = {}
    fake_connector = types.ModuleType("snowflake.connector")
    fake_connector.connect = lambda **kwargs: captured.update(kwargs) or "connection"
    fake_package = types.ModuleType("snowflake")
    fake_package.connector = fake_connector
    monkeypatch.setitem(sys.modules, "snowflake", fake_package)
    monkeypatch.setitem(sys.modules, "snowflake.connector", fake_connector)
    monkeypatch.setenv("HOME", "/home/tester")

    settings = SnowflakeSettings(
        account="org-account",
        user="DQ_CI_USER",
        role="DQ_CI_ROLE",
        warehouse="DQ_WH",
        database="DQ_DEMO",
        private_key_path="~/.snowflake/key.p8",
    )

    assert connect(settings) == "connection"
    assert captured["account"] == "org-account"
    assert captured["role"] == "DQ_CI_ROLE"
    assert captured["private_key_file"] == "/home/tester/.snowflake/key.p8"
    assert "password" not in captured
