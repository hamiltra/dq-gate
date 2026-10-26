"""Convert dbt's ``run_results.json`` to JUnit XML so CI can show each model and test on the PR.

Each result becomes one test case, grouped into a suite per resource type (model, test,
unit_test, ...). dbt statuses map as follows: success/pass -> passed, warn -> passed with the
warning in system-out, fail -> failure, error -> error, skipped -> skipped.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

# Generic test ids end in a 10-character hash, e.g. test.dq_gate.not_null_x_id.1a2b3c4d5e
_HASH_SUFFIX = re.compile(r"\.[0-9a-f]{10}$")

FAILURE_STATUSES = {"fail"}
ERROR_STATUSES = {"error", "runtime error"}


def case_name(unique_id: str) -> str:
    """``test.dq_gate.not_null_x_id.1a2b3c4d5e`` -> ``not_null_x_id``."""
    parts = unique_id.split(".", 2)
    name = parts[2] if len(parts) == 3 else unique_id
    return _HASH_SUFFIX.sub("", name)


def _message(result: dict) -> str:
    message = result.get("message") or result["status"]
    failures = result.get("failures")
    return f"{failures} failing rows: {message}" if failures else message


def to_junit(run_results: dict, suite_prefix: str = "dbt") -> str:
    suites: dict[str, ET.Element] = {}
    root = ET.Element("testsuites", name=suite_prefix)
    for result in run_results["results"]:
        resource_type = result["unique_id"].split(".", 1)[0]
        suite = suites.get(resource_type)
        if suite is None:
            suite = ET.SubElement(root, "testsuite", name=f"{suite_prefix}.{resource_type}")
            suites[resource_type] = suite
        case = ET.SubElement(
            suite,
            "testcase",
            name=case_name(result["unique_id"]),
            classname=f"{suite_prefix}.{resource_type}",
            time=f"{result.get('execution_time') or 0:.3f}",
        )
        status = result["status"]
        if status in FAILURE_STATUSES:
            ET.SubElement(case, "failure", message=_message(result)).text = result["unique_id"]
        elif status in ERROR_STATUSES:
            ET.SubElement(case, "error", message=_message(result)).text = result["unique_id"]
        elif status == "skipped":
            ET.SubElement(case, "skipped", message=result.get("message") or "skipped")
        elif status == "warn":
            ET.SubElement(case, "system-out").text = f"warn: {_message(result)}"

    for suite in suites.values():
        cases = suite.findall("testcase")
        suite.set("tests", str(len(cases)))
        suite.set("failures", str(sum(1 for c in cases if c.find("failure") is not None)))
        suite.set("errors", str(sum(1 for c in cases if c.find("error") is not None)))
        suite.set("skipped", str(sum(1 for c in cases if c.find("skipped") is not None)))
        suite.set("time", f"{sum(float(c.get('time')) for c in cases):.3f}")

    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True) + "\n"
