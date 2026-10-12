# DQ Gate: handoff notes for a new chat

Start a new chat in the **2026 Employment** project and say: "Read `claude/dq-gate-handoff.md` and `claude/dq-gate-project-plan.md`, then continue the DQ Gate project from the next milestone."

## Why this project exists

Target role (from a JD): **Data Quality & Test Automation Engineer**, 6-month remote contract, platform engineering team. Core asks: Python, dbt (ideally Enterprise), Snowflake (including data metric functions), GitLab CI/CD, REST APIs, ServiceNow change management, Jira/QTest, building automation from scratch, and building with AI development tools (Windsurf, Devin or similar).

Gaps identified against Roger's background (strong on Python validation frameworks, replacing commercial tools, Snowflake/dbt evaluation): GitLab CI/CD, ServiceNow change control via API, Snowflake data metric functions, dbt testing in CI, coverage-gating, AI-tool evidence.

## Skills priority order

1. GitLab CI/CD (pipelines, merge-request gates)
2. dbt testing (generic, singular, unit tests, freshness, slim CI)
3. Snowflake native data quality (data metric functions; needs Enterprise edition)
4. ServiceNow change management via REST API (free personal developer instance)
5. Python for integrations (requests, pytest, optional FastAPI)
6. Documented use of AI coding tools
7. Test coverage gating for changed dbt models

Lower priority: QTest/Tosca (know what they do), agent-based CI automation (stretch), more governance work (already a strength).

## The project

A GitHub Actions pipeline that runs dbt tests and Snowflake data quality checks on synthetic financial data, blocks a merge or deploy when changed models lack tests, and creates a ServiceNow change request with evidence attached. Deploy job waits for change approval.

Full plan, milestones M0-M7 and checklists: `claude/dq-gate-project-plan.md` (also `docs/PROJECT_PLAN.md` in the repo).

## Decisions made

- **Oct 12 update:** Roger chose to build and run CI in **GitHub** (GitHub Actions) and set the JD's GitLab emphasis aside. The project design is otherwise unchanged. (The "GitLab CI/CD" skills notes above describe the JD, not this project.)

- **Start date:** Monday Oct 12, 2026. Work window Oct 12 - Nov 8, buffer to Nov 15.
- **Snowflake trial:** start Oct 17-18 (Enterprise edition), so it covers Weeks 2-4.
- **Data:** synthetic only. No real or proprietary data or designs from current or former employers.
- **dbt in Docker:** yes. Plan is a small custom image (python slim + pinned dbt-core and dbt-snowflake) in the GitHub Container Registry (ghcr.io), used for CI and local runs.
- **Networking:** dbt connects outbound to Snowflake over HTTPS; nothing needs inbound access to the home network. Start with GitHub-hosted runners; a self-hosted runner on the homelab (separate VLAN, no fork pull requests) is optional. Do not restrict Snowflake by IP if using hosted runners.
- **Inbound access** would only be needed for the optional FastAPI stretch service; Tailscale would cover it.

## What is built (M0-M1 scaffold, delivered as dq-gate.zip)

- Repo `dq-gate` with `.github/workflows/ci.yml` (lint and unit-tests jobs on pull requests and `main`, JUnit and coverage artifacts), Dependabot config, PR template
- `src/dq_tools/` with env-based config and a ServiceNow client skeleton (calls stubbed for M2)
- 7 passing pytest tests, ruff clean, Makefile, pre-commit config, `.env.example`, pull request template
- Placeholders for `dbt/`, `scripts/`, `docs/AI_WORKFLOW.md`
- Pushed to github.com/hamiltra/dq-gate on Oct 12; the workflow has not yet run on GitHub

## Next steps

1. Monday Oct 12: M0 (repo pushed to GitHub; remaining: `make setup`, `make check`, `pre-commit autoupdate`, request ServiceNow instance)
2. M1: add a branch ruleset on `main` requiring a pull request and the `lint` and `unit-tests` checks, open a pull request, break a test on purpose to confirm it blocks the merge
3. M2: implement the ServiceNow client against the personal developer instance (create change request, work note, attachment) with mocked tests
4. Optionally add a Dockerfile, docker-compose file and runner notes before M3

## Open items in the original chat

The Thursday Oct 8, 10 AM reminder to refactor the PIMCO structure on the resume and LinkedIn is set to arrive in the **original** chat, not a new one. Context for that: LinkedIn shows promotion to Senior Software Developer in Jan 2017; resume and LinkedIn job titles differ; merge duplicate 2017/2018-2023 entries; use the "$150K annually over a 10+ year period" wording; add "Designing RESTful APIs" certification to the resume; confirm exact titles and dates.
