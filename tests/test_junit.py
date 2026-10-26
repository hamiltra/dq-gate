import xml.etree.ElementTree as ET

from dq_tools.junit import case_name, to_junit


def result(unique_id, status, message=None, failures=None, execution_time=0.5):
    return {
        "unique_id": unique_id,
        "status": status,
        "message": message,
        "failures": failures,
        "execution_time": execution_time,
    }


RUN_RESULTS = {
    "results": [
        result("model.dq_gate.stg_prices", "success", "SUCCESS 1"),
        result("model.dq_gate.dim_security", "skipped", "SKIP"),
        result("test.dq_gate.not_null_stg_prices_id.0123456789", "pass"),
        result("test.dq_gate.assert_prices_positive", "fail", "Got 1 result", failures=1),
        result("test.dq_gate.unique_stg_prices_id.abcdef0123", "warn", "Got 2 results", failures=2),
        result("test.dq_gate.broken_test", "error", "Database Error: bad SQL"),
        result("unit_test.dq_gate.fct_value.test_logic", "pass"),
    ]
}


def parse():
    return ET.fromstring(to_junit(RUN_RESULTS))


def test_case_name_strips_type_package_and_hash():
    assert case_name("test.dq_gate.not_null_stg_prices_id.0123456789") == "not_null_stg_prices_id"
    assert case_name("test.dq_gate.assert_prices_positive") == "assert_prices_positive"
    assert case_name("unit_test.dq_gate.fct_value.test_logic") == "fct_value.test_logic"
    assert case_name("model.dq_gate.stg_prices") == "stg_prices"


def test_one_suite_per_resource_type_with_counts():
    suites = {s.get("name"): s for s in parse().findall("testsuite")}
    assert list(suites) == ["dbt.model", "dbt.test", "dbt.unit_test"]
    model = suites["dbt.model"]
    assert (model.get("tests"), model.get("skipped"), model.get("failures")) == ("2", "1", "0")
    test = suites["dbt.test"]
    assert (test.get("tests"), test.get("failures"), test.get("errors")) == ("4", "1", "1")
    assert test.get("time") == "2.000"


def test_status_mapping():
    cases = {c.get("name"): c for c in parse().iter("testcase")}
    failure = cases["assert_prices_positive"].find("failure")
    assert failure.get("message") == "1 failing rows: Got 1 result"
    assert failure.text == "test.dq_gate.assert_prices_positive"
    assert cases["broken_test"].find("error").get("message") == "Database Error: bad SQL"
    assert cases["dim_security"].find("skipped") is not None
    assert (
        cases["unique_stg_prices_id"].find("system-out").text
        == "warn: 2 failing rows: Got 2 results"
    )
    passed = cases["not_null_stg_prices_id"]
    assert list(passed) == [] and passed.get("classname") == "dbt.test"


def test_output_is_an_xml_document():
    assert to_junit({"results": []}).startswith("<?xml version='1.0' encoding='utf-8'?>")
