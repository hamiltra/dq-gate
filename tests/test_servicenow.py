import json

import pytest
import requests
import responses

from dq_tools.servicenow import ServiceNowClient, ServiceNowError

BASE = "https://dev12345.service-now.com"
TABLE_URL = f"{BASE}/api/now/table/change_request"


def make_client() -> ServiceNowClient:
    return ServiceNowClient(f"{BASE}/", "svc_dq", "secret")


def test_requires_https():
    with pytest.raises(ValueError):
        ServiceNowClient("http://dev12345.service-now.com", "u", "p")


def test_url_building_handles_slashes():
    client = make_client()
    assert client.url("/api/now/table/change_request") == TABLE_URL
    assert client.url("api/now/table/change_request") == TABLE_URL


def test_session_uses_basic_auth_and_json_accept():
    client = make_client()
    assert client.session.auth == ("svc_dq", "secret")
    assert client.session.headers["Accept"] == "application/json"


@responses.activate
def test_create_change_request_posts_payload_and_returns_record():
    responses.post(
        TABLE_URL,
        json={"result": {"sys_id": "abc123", "number": "CHG0030001"}},
        status=201,
    )

    record = make_client().create_change_request("Deploy v1", "Release notes")

    assert record["sys_id"] == "abc123"
    assert record["number"] == "CHG0030001"
    sent = json.loads(responses.calls[0].request.body)
    assert sent == {
        "short_description": "Deploy v1",
        "description": "Release notes",
        "type": "normal",
    }


@responses.activate
def test_add_work_note_patches_work_notes_field():
    responses.patch(f"{TABLE_URL}/abc123", json={"result": {"sys_id": "abc123"}})

    result = make_client().add_work_note("abc123", "Tests passed")

    assert result["sys_id"] == "abc123"
    assert json.loads(responses.calls[0].request.body) == {"work_notes": "Tests passed"}


@responses.activate
def test_attach_file_sends_bytes_with_table_params(tmp_path):
    report = tmp_path / "report.txt"
    report.write_bytes(b"evidence")
    responses.post(
        f"{BASE}/api/now/attachment/file",
        json={"result": {"sys_id": "att1", "file_name": "report.txt"}},
        status=201,
    )

    result = make_client().attach_file("abc123", report)

    assert result["file_name"] == "report.txt"
    request = responses.calls[0].request
    assert "table_name=change_request" in request.url
    assert "table_sys_id=abc123" in request.url
    assert "file_name=report.txt" in request.url
    assert request.headers["Content-Type"] == "text/plain"


@responses.activate
def test_error_response_raises_with_status_and_message_but_no_secrets():
    responses.post(
        TABLE_URL,
        json={"error": {"message": "User Not Authenticated"}},
        status=401,
    )

    with pytest.raises(ServiceNowError) as excinfo:
        make_client().create_change_request("Deploy")

    message = str(excinfo.value)
    assert "401" in message
    assert "User Not Authenticated" in message
    assert "secret" not in message


@responses.activate
def test_non_json_error_body_falls_back_to_reason():
    responses.post(TABLE_URL, body="<html>sleeping</html>", status=503)

    with pytest.raises(ServiceNowError, match="503"):
        make_client().create_change_request("Deploy")


@responses.activate
def test_unexpected_success_body_raises():
    responses.post(TABLE_URL, json={"unexpected": True}, status=200)

    with pytest.raises(ServiceNowError, match="unexpected response"):
        make_client().create_change_request("Deploy")


@responses.activate
def test_network_failure_is_wrapped():
    responses.post(TABLE_URL, body=requests.ConnectionError("boom"))

    with pytest.raises(ServiceNowError, match="ConnectionError"):
        make_client().create_change_request("Deploy")


@responses.activate
def test_get_change_reads_number_state_and_approval():
    responses.get(
        f"{TABLE_URL}/abc123",
        json={"result": {"number": "CHG0030002", "state": "-2", "approval": "approved"}},
    )

    client = make_client()
    assert client.get_change("abc123") == {
        "number": "CHG0030002",
        "state": "-2",
        "approval": "approved",
    }
    assert "sysparm_fields=number%2Cstate%2Capproval" in responses.calls[0].request.url
    assert client.get_change_state("abc123") == "-2"


@responses.activate
def test_set_change_state_patches_state_and_optional_note():
    responses.patch(f"{TABLE_URL}/abc123", json={"result": {"sys_id": "abc123", "state": "0"}})

    client = make_client()
    client.set_change_state("abc123", "0", note="Deployed")
    client.set_change_state("abc123", "0")
    client.set_change_state("abc123", "0", fields={"work_end": "2026-10-27 19:50:00", "state": "x"})

    assert json.loads(responses.calls[0].request.body) == {"state": "0", "work_notes": "Deployed"}
    assert json.loads(responses.calls[1].request.body) == {"state": "0"}
    # the explicit state argument wins over a state passed in fields
    assert json.loads(responses.calls[2].request.body) == {
        "work_end": "2026-10-27 19:50:00",
        "state": "0",
    }
