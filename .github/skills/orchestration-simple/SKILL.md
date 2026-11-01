---
name: orchestration-simple
description: 'Manager-only Simple mode orchestration for straightforward Python features and bug fixes: developer, independent tester, reviewer, and bounded source-only correction loops.'
user-invocable: false
---

# Simple Orchestration

Run this workflow ONLY as `manager`, after the user chooses Simple mode. If you
are a worker and this skill is loaded, do not invoke agents or run the pipeline;
return your assigned report to manager. There is no analytic or architect phase.

Follow the [manager contract](../../agents/manager.agent.md) and
[Python skill](../lang-python/SKILL.md). Manager owns every invocation, the
requirement contract, approval gates, and the shared `correction_count`.

## Initial Pipeline

1. **Prepare**: manager confirms the original goal, numbered requirements,
   observable acceptance criteria, exclusions, allowed paths, and verification
   expectations. Ask the user about missing expected behavior before developing.
   Start the correction count at `0`. Pass the full contract to every worker.
2. **Develop**: manager invokes `developer` with the contract and relevant
   implementation context. Developer edits production code only within assigned
   paths, runs existing focused checks, and returns `DONE` or `BLOCKED`. Manager
   receives the report and diff. `DONE` is not an overall approval.
3. **Test**: manager invokes `tester` with the original requirements, acceptance
   criteria, and separately labeled developer report. Tester defines expected
   behavior from requirements before inspecting implementation internals, writes
   independent pytest tests under `tests/`, and runs focused and full checks.
   `FAIL` goes to the correction loop; `BLOCKED` goes to manager for clarification.
4. **Review**: only after tester `PASS`, manager invokes `reviewer` with the
   contract, integrated change, test diff, preserved failure evidence, and actual
   verification results. Reviewer performs read-only review and returns
   `APPROVED`, `CHANGES_REQUESTED`, or `BLOCKED`.
5. **Complete**: manager reports `COMPLETE` only when acceptance criteria are
   satisfied, required checks passed for the current change, and review approved.
   Include the chosen mode, changed files, check results, and correction count.

## Correction Loop

- On tester `FAIL`, manager classifies findings using the
  [failure-routing and approval rules](../../agents/manager.agent.md#corrections-and-blockers),
  then checks the ten-cycle budget and increments before each corrective
  assignment or batch. Dispatch the responsible owner with requirement IDs,
  unchanged failing expectations, expected versus observed behavior, and
  tracebacks. Manager then invokes tester to rerun preserved regressions and full
  gates. If `PASS`, manager invokes reviewer; otherwise repeat within the budget.
- On reviewer production findings, manager allocates the next correction cycle,
  dispatches developer, then tester, then reviewer. No edit may bypass retesting.
- On reviewer missing-test findings, manager allocates a correction cycle to
  tester to add tests from the existing requirements. Preserve failing assertions.
  If the additions fail, allocate the next cycle to developer's source repair.
  If they pass, send the updated tests and evidence back to reviewer.
- Never give developer permission to edit tests or change quality thresholds.
  Genuine invalid test assumptions require user clarification and explicit
  approval, not silently rewritten expectations.
- Initial execution is cycle `0`. One correction includes its following test
  rerun and review; those verifications do not increment separately. All failure
  and review paths share a maximum of `10` corrective cycles. Do not reset it.
- After cycle `10`, allow its verification and review to finish. If unresolved,
  stop before another corrective dispatch and return `NEEDS_USER_INPUT` with
  outstanding findings, attempted fixes, preserved evidence, and the count.
- On genuine `BLOCKED` reports, missing requirements, unavailable tooling, or
  permissions, manager resolves only authorized issues or asks the user. Do not
  retry an unchanged blocker, skip an unrun gate, or report success prematurely.

## Verification Gates

Tester runs the focused tests first, then the existing repository gates:

```sh
uv run pytest tests/
uv run pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

Capture command exit statuses, test counts, coverage, skips, and lint/format
results. Pre-existing or environment failures must be identified explicitly;
they are not evidence that the current task passed. Any edit after a passing
report requires fresh applicable verification and review before completion.

## Invocation

This section is the shared entry-point and client guidance for both Simple and
Advanced mode. Reading it does not select Simple mode. Select
[manager](../../agents/manager.agent.md) and provide the task and acceptance
criteria; manager asks for a mode unless your request already specifies one.

### VS Code Local

Select manager in the agent picker or run the
[orchestrate prompt](../../prompts/orchestrate.prompt.md) from Chat:

```text
/orchestrate Simple <task and acceptance criteria>
/orchestrate Advanced <task and acceptance criteria>
```

Omit the mode to have manager ask you to choose. The prompt can also be started
with **Chat: Run Prompt** or its Run button; it inherits manager's tools.
Reload/discover customizations after updating profiles. Local honors manager's
named `agents` allowlist; workers are hidden from the picker and cannot delegate.

### Copilot CLI

Restart CLI after updating profiles, then select manager with `/agent` or start
an interactive session with `copilot --agent manager`. For noninteractive work,
provide the mode and complete acceptance criteria:

```sh
copilot --agent manager --prompt "Use Simple mode: <task and acceptance criteria>"
```

The Local-only `agents` field is not a CLI allowlist. CLI subagents do not
automatically inherit repository instructions, so these profiles explicitly ask
workers to read the project instructions and Python skill. CLI supports
`strict-tools-list: true` for tighter filtering; it is not a portable Local
setting and is not enabled in the shared profiles. `/orchestrate` prompt files
are a VS Code Local entry point, not an assumed CLI slash command.

### App and Cloud Clients

In the GitHub Copilot app, choose manager in the agent picker or with `/agent`.
Repository agents and skills are supported, but verify the installed runtime's
delegation/tool restrictions instead of assuming Local semantics.

GitHub.com cloud agent also supports custom profiles. Select manager and supply
the mode and acceptance criteria upfront; tool, invocation, environment, and
clarification behavior differ from Local. Do not assume the VS Code slash
prompt exists in app or cloud clients.

### Compatibility and Verification Limits

Profiles use shared tool aliases without a fixed model or runtime target. Only
manager may delegate within this workflow, but this is not a global caller-ID
restriction on unrelated agents. Workers remain model-invocable for CLI/app
compatibility; runtime-required default tools may differ outside Local. Worker
instructions prohibit delegation, but identical enforcement across clients is
not guaranteed. File ownership and the ten-cycle limit are instructions, not a
filesystem sandbox or deterministic workflow engine.

Validation covered YAML/tool contracts, local links, and a live read-only
Copilot CLI manager -> analytic discovery/delegation smoke test with editing and
command tools disabled. Full development/repair loops and app/cloud execution
have not been runtime-tested.

