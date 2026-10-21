import pytest

from dq_tools.config import ConfigError, ServiceNowSettings, SnowflakeSettings


def test_servicenow_settings_from_env():
    env = {
        "SERVICENOW_INSTANCE": "https://dev12345.service-now.com",
        "SERVICENOW_USER": "svc_dq",
        "SERVICENOW_PASSWORD": "secret",
    }
    settings = ServiceNowSettings.from_env(env)
    assert settings.instance == "https://dev12345.service-now.com"
    assert settings.user == "svc_dq"
    assert settings.password == "secret"


def test_servicenow_settings_reports_all_missing_variables():
    with pytest.raises(ConfigError) as excinfo:
        ServiceNowSettings.from_env({"SERVICENOW_USER": "svc_dq"})
    message = str(excinfo.value)
    assert "SERVICENOW_INSTANCE" in message
    assert "SERVICENOW_PASSWORD" in message
    assert "SERVICENOW_USER" not in message


SNOWFLAKE_ENV = {
    "SNOWFLAKE_ACCOUNT": "org-account",
    "SNOWFLAKE_USER": "DQ_CI_USER",
    "SNOWFLAKE_ROLE": "DQ_CI_ROLE",
    "SNOWFLAKE_WAREHOUSE": "DQ_WH",
    "SNOWFLAKE_DATABASE": "DQ_DEMO",
    "SNOWFLAKE_PRIVATE_KEY_PATH": "/tmp/key.p8",
}


def test_snowflake_settings_from_env():
    settings = SnowflakeSettings.from_env(SNOWFLAKE_ENV)
    assert settings.account == "org-account"
    assert settings.role == "DQ_CI_ROLE"
    assert settings.private_key_path == "/tmp/key.p8"


def test_snowflake_settings_reports_missing_variables():
    env = {k: v for k, v in SNOWFLAKE_ENV.items() if k != "SNOWFLAKE_PRIVATE_KEY_PATH"}
    with pytest.raises(ConfigError, match="SNOWFLAKE_PRIVATE_KEY_PATH"):
        SnowflakeSettings.from_env(env)
