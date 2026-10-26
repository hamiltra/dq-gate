"""Test coverage gate for changed dbt models.

A model counts as changed when its SQL file or its properties YAML (where its tests are declared)
appears in the diff, so deleting a model's tests in the YAML is caught too.

A changed model passes when at least one data test covers it: a generic test attached to it
(``attached_node``) or a singular test that refs it. Unit tests are reported but do not count on
their own, because they check the SQL logic against fixed inputs, not the data the model produces.

Everything here works on a parsed ``manifest.json`` dict and a list of changed paths, so it is
unit-tested without dbt, git or Snowflake.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

DBT_PROJECT_DIR = "dbt/dq_gate"
COMMENT_MARKER = "<!-- dq-gate:coverage-gate -->"


@dataclass(frozen=True)
class ModelCoverage:
    unique_id: str
    name: str
    path: str
    data_tests: tuple[str, ...]
    unit_tests: tuple[str, ...]

    @property
    def covered(self) -> bool:
        return bool(self.data_tests)


def _project_relative(path: str) -> str:
    """Strip the ``<package>://`` prefix dbt puts on ``patch_path``."""
    return path.split("://", 1)[-1]


def changed_models(
    manifest: dict, changed_paths: Iterable[str], project_dir: str = DBT_PROJECT_DIR
) -> list[str]:
    """Unique ids of models whose SQL or properties YAML is in ``changed_paths`` (repo-relative)."""
    prefix = project_dir.rstrip("/") + "/"
    changed = {p.removeprefix(prefix) for p in changed_paths if p.startswith(prefix)}
    hits = []
    for uid, node in manifest["nodes"].items():
        if node["resource_type"] != "model":
            continue
        files = {node["original_file_path"]}
        if node.get("patch_path"):
            files.add(_project_relative(node["patch_path"]))
        if files & changed:
            hits.append(uid)
    return sorted(hits)


def model_tests(manifest: dict) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Map each model id to the data tests and the unit tests that cover it."""
    data: dict[str, list[str]] = {}
    unit: dict[str, list[str]] = {}
    for uid, node in manifest["nodes"].items():
        if node["resource_type"] != "test":
            continue
        # A relationships test also depends on the model it points at; only the model it is
        # attached to is the one being tested. Singular tests have no attached node.
        targets = (
            [node["attached_node"]] if node.get("attached_node") else node["depends_on"]["nodes"]
        )
        for target in targets:
            data.setdefault(target, []).append(uid)
    for uid, node in manifest.get("unit_tests", {}).items():
        for target in node["depends_on"]["nodes"]:
            unit.setdefault(target, []).append(uid)
    return data, unit


def evaluate(
    manifest: dict, changed_paths: Iterable[str], project_dir: str = DBT_PROJECT_DIR
) -> list[ModelCoverage]:
    data, unit = model_tests(manifest)
    results = []
    for uid in changed_models(manifest, changed_paths, project_dir):
        node = manifest["nodes"][uid]
        results.append(
            ModelCoverage(
                unique_id=uid,
                name=node["name"],
                path=f"{project_dir}/{node['original_file_path']}",
                data_tests=tuple(sorted(data.get(uid, []))),
                unit_tests=tuple(sorted(unit.get(uid, []))),
            )
        )
    return results


def summary_markdown(results: list[ModelCoverage]) -> str:
    """Markdown for the job summary and the pull request comment."""
    lines = [COMMENT_MARKER, "## Coverage gate", ""]
    if not results:
        lines.append("No dbt models changed in this pull request.")
        return "\n".join(lines) + "\n"
    missing = [r for r in results if not r.covered]
    if missing:
        lines.append(
            f"**Failed:** {len(missing)} of {len(results)} changed models have no data tests."
        )
    else:
        lines.append(f"**Passed:** all {len(results)} changed models have data tests.")
    lines += ["", "| Model | Data tests | Unit tests | Result |", "|---|---:|---:|---|"]
    for r in results:
        result = "pass" if r.covered else "**missing tests**"
        lines.append(
            f"| `{r.name}` (`{r.path}`) | {len(r.data_tests)} | {len(r.unit_tests)} | {result} |"
        )
    if missing:
        lines += [
            "",
            "Add at least one data test (a generic test in the model's YAML or a singular test "
            "that refs it) to each model marked **missing tests**.",
        ]
    return "\n".join(lines) + "\n"
