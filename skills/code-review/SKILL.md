---
name: code-review
description: Use when a change is ready, to review code through a subagent before calling it done. Covers correctness, comment quality, security holes, and bugs, judged against the project and its use case, and persists the report under .agents/.
---

# Code Review

Before you call a change done, have a subagent review it: a fresh context reads
the code without your assumptions.

## What the subagent checks

- Comments: do they explain intent, and are they accurate?
- Code quality: is it clean, minimal, and free of leftovers?
- Security holes and bugs.
- The project and its use case: does the change fit the whole, not just the
  lines it touches?

## The report

Let the subagent write its findings to `.agents/review.md` in the project
directory, the way the work log is kept. Note each finding as a short line:
what is wrong, where, and how severe. Say in the chat that the report exists.

Act on the findings before finishing, or explain in the chat why a finding
does not apply.
