import pytest

from dq_tools.config import ConfigError, ServiceNowSettings


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
