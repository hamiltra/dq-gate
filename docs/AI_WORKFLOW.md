# AI-assisted development log

How AI tools were used to build DQ Gate, what they got wrong, and how that was caught. The facts
come from the repository history, the runbooks and the pull requests. The two sections on review
and trust are my own judgment.

## Tools used

| Tool | Used for |
|---|---|
| Claude (chat) | M0–M4: planning, and generating each milestone as a bundle (code, tests, runbook) that I applied, ran and committed |
| Claude Code (VS Code) | Repo cleanup and `CLAUDE.md`, the Dependabot backlog, M5 (coverage gate, JUnit, PR comment), M6 (ServiceNow deploy gate), M7 polish; commits and pull requests through `gh` |

## How the work was split

- I owned the accounts, credentials and every approval: the Snowflake and ServiceNow setup, GitHub
  secrets, merges, and approving each production change in ServiceNow.
- The AI wrote code, tests, workflows and documentation. In the chat milestones (M3, M4) it could
  not reach Snowflake, so each runbook ended with a section on **what was and was not verified**,
  and I ran the live steps and reported errors back.
- In Claude Code (M5 onward) it also checked its work against the real services before asking me
  to merge: read-only queries against Snowflake and ServiceNow, real dbt artifacts from CI runs,
  live test changes on the developer instance, and demonstration commits on the pull request.

## What worked

- **Looking at real data before writing code.** The M5 coverage gate was built against a real
  `manifest.json`, and the JUnit converter against a real `run_results.json` downloaded from a CI
  run, not against the documented schema.
- **Probing the live services before designing.** M6 started by reading an existing change
  request (to see the real `state` and `approval` values) and the Snowflake grants (to confirm
  the CI role could deploy to production) before any code was written.
- **Proving each gate on a real pull request.** PR #23 added a model without tests (coverage gate
  failed, merge blocked), then added tests (gate passed). The M6 timeout and re-run path was
  exercised for real on the first production deploy.
- **Small, reviewable pull requests** with a description of what was verified, and the required
  checks running on every one.

## Where generated output or assumptions were wrong, and how it was caught

| What happened | How it was caught |
|---|---|
| The M5 task brief said `scripts/coverage_gate.py` and its tests "are already written and pass". They did not exist anywhere. | Checked the repo, its history and the disk before starting; stopped and asked instead of building on the assumption. |
| The M4 docs pull request was merged, but the M4 code pull request (#19) was still open, so the README described code that was not on `main`. | Found while writing `CLAUDE.md`, by comparing the README with the files on `main`. |
| Zip bundles and editor swap files were committed (M3, M4), and a personal notes file was in the public repo. | Found during repo review; removed, git-ignored, and the full history scanned for secrets in M7 (none found). |
| A helper named `tests_by_model` was collected by pytest as a test and errored. | The test run; renamed to `model_tests`. |
| Advice to merge two blocked Dependabot pull requests with `gh pr merge --admin`. | Reading the ruleset showed nobody can bypass it. The blocks cleared once the branches were rebased. |
| Three Dependabot pull requests showed failing `dbt-build` checks. | The runs pre-dated the fix that skips `dbt-build` for Dependabot (no secrets); rebasing gave fresh, passing results. |
| Moving a ServiceNow change to Review failed with HTTP 403. | Live test on the developer instance. The full error named the business rule *Actual Start/End Date Validation*; the deploy now sets the actual end time itself. |
| A 15-minute approval window was too short for a two-stage approval done by hand. | The first production deploy timed out at the CAB stage; the documented re-run path worked as designed. |

## What I reviewed or rewrote by hand, and why

For milestones M0-M4, I worked side-by-side with Claude.ai doing the cutting and pasting. I did this until I began fully understanding all of the workflow processes between GitHub, ServiceNow and Snowflake. I checked about 30% along the way to ensure that the application was progressing correctly. Milestones M5-M7 were with using VS Code and Claude Code plugins to assist with the development and streamline the overall progress. Putting Claude Code into the workflow speeded up the progress by 5-6x.

## Where I stopped trusting generated output

I now verify some of the code but focus more on making sure that the process functions with the correct requirements and process works as a user would expect. Sometimes Claude would make mistakes, however, it would often correct itself. Sometimes I would notice in the process that something Claude would try to do that I knew would fail and would wait for Claude to pause for input along the way.

## Guardrails

- Required checks on `main`: `lint`, `unit-tests`, `dbt-build` and `coverage-gate`. Generated code
  is merged only after they pass.
- Unit tests never call live services: ServiceNow HTTP is mocked, Snowflake code runs against
  fake connections, and the deploy gate's wait loop runs on a fake clock.
- Secrets live only in GitHub Actions secrets and a local, git-ignored `.env`. Snowflake uses
  key-pair authentication; ServiceNow uses a dedicated least-privilege integration user.
- Live checks against Snowflake and ServiceNow are read-only unless the task needs a write
  (the test changes CHG0030002 and later are synthetic).
- Production deploys need a human approval in ServiceNow; the pipeline cannot approve its own
  change.
- No secrets or real employer data in prompts; all data is synthetic.
