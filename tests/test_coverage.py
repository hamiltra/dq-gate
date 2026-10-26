from dq_tools.coverage import (
    COMMENT_MARKER,
    changed_models,
    evaluate,
    model_tests,
    summary_markdown,
)

P = "dbt/dq_gate"


def model(name, folder="marts", yml="_marts.yml"):
    node = {
        "resource_type": "model",
        "name": name,
        "original_file_path": f"models/{folder}/{name}.sql",
        "patch_path": f"dq_gate://models/{folder}/{yml}" if yml else None,
    }
    return f"model.dq_gate.{name}", node


def generic_test(name, attached, depends=None):
    return f"test.dq_gate.{name}.0123456789", {
        "resource_type": "test",
        "attached_node": attached,
        "depends_on": {"nodes": depends or [attached]},
    }


def singular_test(name, depends):
    return f"test.dq_gate.{name}", {
        "resource_type": "test",
        "attached_node": None,
        "depends_on": {"nodes": depends},
    }


def make_manifest():
    nodes = dict(
        [
            model("stg_securities", "staging", "_staging.yml"),
            model("dim_security"),
            model("fct_value"),
            model("mart_new", yml=None),
            generic_test("unique_stg_securities_id", "model.dq_gate.stg_securities"),
            generic_test("not_null_dim_security_id", "model.dq_gate.dim_security"),
            # relationships test on fct_value that also depends on stg_securities
            generic_test(
                "relationships_fct_value_security_id",
                "model.dq_gate.fct_value",
                ["model.dq_gate.stg_securities", "model.dq_gate.fct_value"],
            ),
            singular_test("assert_dim_ok", ["model.dq_gate.dim_security"]),
        ]
    )
    unit_tests = {
        "unit_test.dq_gate.mart_new.test_logic": {
            "depends_on": {"nodes": ["model.dq_gate.mart_new"]}
        }
    }
    return {"nodes": nodes, "unit_tests": unit_tests}


def test_changed_models_matches_sql_files():
    m = make_manifest()
    assert changed_models(m, [f"{P}/models/marts/dim_security.sql", "README.md"]) == [
        "model.dq_gate.dim_security"
    ]


def test_changed_models_includes_every_model_in_a_changed_yaml():
    m = make_manifest()
    assert changed_models(m, [f"{P}/models/marts/_marts.yml"]) == [
        "model.dq_gate.dim_security",
        "model.dq_gate.fct_value",
    ]


def test_changed_models_ignores_paths_outside_the_project():
    m = make_manifest()
    assert changed_models(m, ["models/marts/dim_security.sql", "scripts/x.py"]) == []


def test_relationships_test_counts_only_for_its_attached_model():
    data, _ = model_tests(make_manifest())
    assert data["model.dq_gate.stg_securities"] == [
        "test.dq_gate.unique_stg_securities_id.0123456789"
    ]
    assert (
        "test.dq_gate.relationships_fct_value_security_id.0123456789"
        in data["model.dq_gate.fct_value"]
    )


def test_singular_tests_cover_the_models_they_ref():
    data, _ = model_tests(make_manifest())
    assert "test.dq_gate.assert_dim_ok" in data["model.dq_gate.dim_security"]


def test_unit_tests_alone_do_not_cover_a_model():
    m = make_manifest()
    [result] = evaluate(m, [f"{P}/models/marts/mart_new.sql"])
    assert result.unit_tests == ("unit_test.dq_gate.mart_new.test_logic",)
    assert result.data_tests == ()
    assert not result.covered


def test_evaluate_passes_tested_models():
    m = make_manifest()
    results = evaluate(m, [f"{P}/models/marts/dim_security.sql"])
    assert [(r.name, len(r.data_tests), r.covered) for r in results] == [("dim_security", 2, True)]
    assert results[0].path == f"{P}/models/marts/dim_security.sql"


def test_summary_reports_missing_tests():
    m = make_manifest()
    text = summary_markdown(
        evaluate(m, [f"{P}/models/marts/mart_new.sql", f"{P}/models/marts/dim_security.sql"])
    )
    assert text.startswith(COMMENT_MARKER)
    assert "**Failed:** 1 of 2 changed models have no data tests." in text
    assert (
        "| `mart_new` (`dbt/dq_gate/models/marts/mart_new.sql`) | 0 | 1 | **missing tests** |"
        in text
    )
    assert "| `dim_security`" in text and "| pass |" in text


def test_summary_passes_and_handles_no_changes():
    m = make_manifest()
    assert "**Passed:** all 1 changed models" in summary_markdown(
        evaluate(m, [f"{P}/models/marts/dim_security.sql"])
    )
    assert "No dbt models changed" in summary_markdown([])
