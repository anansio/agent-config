---
name: global-rules
description: Always-on baseline rules for every task in every project. Load this skill at the start of every session and follow it throughout; it is not optional and does not depend on the task. The bundled references hold the planning, logging, security, cleanup, accessibility, and coding rules.
---

# Global Rules

## Language

Write in English: code, comments, commit messages, docs, and these rules.

## Documentation of intent

Write down decisions and their reasons as they stand. Do not leave notes that
only made sense during the discussion.

## Keeping the user in the loop

Say in a line what you are about to do and why, and after each step what the
result was and what comes next. Keep it short. The user follows the work in the
chat, not in the tool output.

## Questions

Ask when a decision is unclear and really matters. Give the context, the
trade-offs, and what you would recommend, with short options to answer. Decide
small, reversible things yourself.

## Subagents

Hand a self-contained piece of work to a subagent to keep your own context
small, and report back what it found.

## Problem solving

Fix the cause, not the symptom, and do not build a workaround around a failure.
When an attempt does not work, undo it instead of stacking more fixes on top;
work out why first, then change course.

## Work log

Keep a short log as you work, and record only features, fixes, and decisions.
Drop or rewrite entries that a later change makes obsolete. See
[logging](references/logging.md).

## Definition of done

A change is done when it is clean and tested. Do not ship untested code, or code
with a known security hole.

## References

- [Planning](references/planning.md): before writing code, for every task.
- [Logging](references/logging.md): for the work log.
- [Security](references/security.md): for anything that ships.
- [Cleanup](references/cleanup.md): after an attempt did not work out.
- [Accessibility](references/accessibility.md): for user interfaces and
  user-facing text.
- [Coding rules](references/coding-rules.md): for writing or changing code.
