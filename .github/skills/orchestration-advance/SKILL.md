---
name: orchestration-advance
description: 'Manager-only Advanced mode orchestration for complex Python tasks: analytic requirements and architecture planning, sequential or parallel developers, independent tester, reviewer, and bounded corrections.'
user-invocable: false
---

# Advanced Orchestration

Run this workflow ONLY as `manager`, after the user chooses Advanced mode. If you
are a worker and this skill is loaded, return your assigned report without
invoking agents. The flow is analytic -> developer -> tester -> reviewer;
analytic includes architecture when needed. There is no architect agent.

Follow the [manager contract](../../agents/manager.agent.md) and
[Python skill](../lang-python/SKILL.md). Manager owns all invocations, user
clarification, dependencies, file ownership, and the shared correction count.

For entry points and client compatibility, see the shared
[invocation guidance](../orchestration-simple/SKILL.md#invocation). Select Advanced
mode to execute this workflow; consulting the shared guidance does not switch
the selected mode.

## Initial Pipeline

1. **Analyze**: manager invokes `analytic` with the original goal, known
   requirements, repository constraints, exclusions, and acceptance expectations.
   On `NEEDS_CLARIFICATION`, manager presents the questions to the user, waits for
   answers, and reinvokes analytic with them. Do not develop while behavior is
   unresolved. `READY` must include numbered requirements, public contracts,
   developer tasks, exact ownership, dependency IDs, a sequential execution
   order, optional parallel groups, and requirement-derived edge-case tests.
2. **Establish the plan**: manager checks that the plan reflects the user's goal
   and confirmed answers. Preserve stable requirement IDs and measurable
   acceptance criteria for every worker. Start `correction_count` at `0`. Choose
   the valid sequential schedule or optional parallel groups as described below.
3. **Develop**: only manager invokes `developer`, once per planned assignment,
   with the complete task contract, assigned write paths, resolved interfaces,
   satisfied dependencies, and required output. Developer returns `DONE` or
   `BLOCKED`; manager receives and combines the reports. Do not treat one
   developer's passing focused tests as verification of the integrated task.
4. **Test the integrated task**: after all required developer assignments finish,
   manager invokes `tester` with the same original acceptance contract, analytic's
   requirement-to-test matrix, and separately labeled implementation reports and
   diffs. Tester derives expected values from requirements, not current code,
   writes independent pytest tests, and runs focused and full verification.
   `FAIL` enters the correction loop; `BLOCKED` goes to manager.
5. **Review**: only after tester `PASS`, manager invokes `reviewer` with the
   contract, plan, integrated change and test diffs, preserved regression evidence,
   and actual verification results. Reviewer returns `APPROVED`,
   `CHANGES_REQUESTED`, or `BLOCKED` without editing files or invoking workers.
6. **Complete**: manager reports `COMPLETE` only after all assignments are
   integrated, all requirements are covered, required checks passed for the
   current change, and reviewer approved. Include chosen mode, verification,
   task ownership/integration notes, changed files, and correction count.

## Parallel Developer Scheduling

- Every assignment needs a unique ID, exact write scope, dependency IDs, shared
  interface contract, and requirement-based acceptance checks.
- Parallelize only assignments with disjoint write scopes, settled interfaces,
  and no unmet dependency. Give shared files and dependency metadata one owner.
- Never schedule two developers to mutate the same file. Serialize shared-file
  work and dependency chains. Wait for a predecessor's report before dispatching
  its dependent assignment; pass the completed outputs explicitly.
- Manager alone launches and joins the work; developers never spawn one another.
  Require all necessary results before invoking tester and reviewer.
- Use the sequential order when parallel delegation is unavailable. Do not create
  branches or assume separate worktrees, shared worker memory, or safe concurrent
  dependency/environment changes.

## Correction Loop

- Tester `FAIL`: manager classifies findings using the
  [failure-routing and approval rules](../../agents/manager.agent.md#corrections-and-blockers),
  then checks the budget and increments before each corrective assignment or
  independent batch. Assign the responsible owner the requirement mismatch,
  unchanged failing expectations, and tracebacks. Manager then dispatches tester
  to rerun preserved regression cases and integrated gates; reviewer runs only
  after `PASS`.
- Reviewer production findings: manager allocates a correction cycle to developer,
  then tester, then reviewer. A passing pre-edit report is no longer sufficient.
- Missing-test findings: manager allocates a correction cycle to tester to add
  requirement-based cases, never to developer. Preserve existing failing
  expectations. If new tests expose a source defect, allocate the next cycle to
  developer. Otherwise return passing updated test evidence to reviewer.
- Never weaken tests, add skips/xfails, reduce thresholds, or alter test
  configuration to force a pass. Invalid specification/test assumptions require
  user clarification and explicit approval of any expectation correction.
- Initial execution is cycle `0`. Increment before each corrective assignment or
  independent corrective batch. Its ensuing test rerun and review stay within
  that cycle. All workers, test failures, and review rejections share ONE budget
  of at most `10` corrective cycles; never reset it for another phase or worker.
- The tenth cycle may finish verification and review, but if unresolved manager
  must stop before an eleventh correction and report `NEEDS_USER_INPUT` with
  outstanding findings, attempted fixes, preserved evidence, and the count.
- On `BLOCKED`, manager clarifies or resolves only authorized issues. Unavailable
  tools, permissions, contradictory requirements, and unrelated failures are not
  reasons to run an endless loop or invent passing results.

## Verification Gates

Tester runs focused regression and cross-assignment integration checks first,
then the existing repository gates against the whole integrated change:

```sh
uv run pytest tests/
uv run pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

Record actual exit statuses, test counts, skip reasons, coverage, and lint/format
results. Do not add mypy, bandit, or other tools solely because the task is in
Advanced mode. Missing/unrun gates, inadequate acceptance coverage, or unresolved
failures cannot produce `PASS` or final approval.
