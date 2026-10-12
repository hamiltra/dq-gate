# dbt project (milestone M3)

Placeholder. In Week 2 this directory will hold the dbt project:

- `dbt_project.yml`, `packages.yml`
- `models/staging`, `models/marts`
- `tests/` for singular tests, schema YAML for generic tests
- `profiles.yml` is **not** committed; CI builds it from masked variables

dbt tooling is kept out of `pyproject.toml` on purpose so its dependencies do not conflict
with the core package. Add a `requirements-dbt.txt` when you start M3.
