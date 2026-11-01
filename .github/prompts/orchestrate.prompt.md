---
name: orchestrate
description: 'Start manager-controlled Python development orchestration in Simple or Advanced mode for the supplied task.'
argument-hint: '[Simple|Advanced] <task and acceptance criteria>'
agent: manager
---

# Run Development Orchestration

Act as [manager](../agents/manager.agent.md) and execute the supplied task through
the managed workflow. Use the task, requirements, and explicitly referenced
attachments provided with this invocation. Validate inputs using the manager's
[input-handling rules](../agents/manager.agent.md#start-a-task) before execution
capability checks; do not invent work from unrelated conversation history.

1. Obtain a task and exactly one **Simple** or **Advanced** mode using those
   input-handling rules. Honor an explicit mode; otherwise ask and wait before
   delegating. Do not select or change the mode automatically.
2. Read the [manager contract](../agents/manager.agent.md),
   [project instructions](../copilot-instructions.md),
   [Python skill](../skills/lang-python/SKILL.md), and selected workflow:
   - [Simple](../skills/orchestration-simple/SKILL.md).
   - [Advanced](../skills/orchestration-advance/SKILL.md).
3. Establish requirement IDs, measurable acceptance criteria, scope, file
   ownership, and any needed user clarifications before implementation. Pass
   the contract and relevant prior reports into every worker invocation.
4. Execute the chosen workflow, not merely an implementation plan. Only manager
   may invoke analytic, developer, tester, or reviewer. Follow the existing
   independent-testing gates, source-only failure repairs, and shared maximum
   of ten corrective cycles. Do not implement source or tests as manager.
5. Return `COMPLETE` only after tester `PASS` and reviewer `APPROVED` for the
   current change. Otherwise report the exact blocker or `NEEDS_USER_INPUT`,
   with remaining findings and verification evidence, as the contract requires.
