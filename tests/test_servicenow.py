import pytest

from dq_tools.servicenow import ServiceNowClient


def make_client() -> ServiceNowClient:
    return ServiceNowClient("https://dev12345.service-now.com/", "svc_dq", "secret")


def test_requires_https():
    with pytest.raises(ValueError):
        ServiceNowClient("http://dev12345.service-now.com", "u", "p")


def test_url_building_handles_slashes():
    client = make_client()
    expected = "https://dev12345.service-now.com/api/now/table/change_request"
    assert client.url("/api/now/table/change_request") == expected
    assert client.url("api/now/table/change_request") == expected


def test_session_uses_basic_auth_and_json_accept():
    client = make_client()
    assert client.session.auth == ("svc_dq", "secret")
    assert client.session.headers["Accept"] == "application/json"


def test_unimplemented_calls_fail_loudly_until_m2():
    client = make_client()
    with pytest.raises(NotImplementedError):
        client.create_change_request("Deploy", "details")
