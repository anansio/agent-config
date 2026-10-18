---
name: global-rules
description: Always-on baseline rules for every task. Covers language, visible reasoning, questions and subagents, problem solving, and the definition of done. Consult the bundled references for accessibility and coding conventions.
---

# Global Rules

These rules apply to every task, in every project.

## Language

Write everything in English: rules, skills, reference documents, code, code
comments, commit messages, and project documentation. English stays precise and
portable across tools and readers worldwide.

## Documentation of intent

State decisions and their reasons as they are. Do not leave in notes that only
made sense during a discussion.

## Visible reasoning

Keep the user able to follow the work in the chat, in short, clear sentences.
- Before non-trivial work: one line, what you will do and why.
- After each step: one line, what the result means (worked or not) and the next step.
- No filler.

## Questions

- Ask with the question tool when a decision is unclear and affects the
  outcome. Decide small, reversible details yourself.
- Give the question full context, a clear recommendation, and the trade-offs.
- Offer short, concrete answer options.

## Subagents

Delegate an isolated, well-scoped subtask to a subagent to keep the main
context small. Summarize the result back.

## Problem solving

- Fix the cause, not the symptom. Do not work around a failure.
- On a failure, diagnose once before changing course. Do not stack fixes.
- Revert attempts that do not work or serve no demonstrated purpose.

## Work log

Keep a short work log while working. Record what was done and why, including
meaningful intermediate steps. Remove or reword entries that a course change
has made obsolete. Note open points that still need attention.

## Definition of done

A change is complete, clean, and tested. Do not deliver code that is untested,
or that introduces a known security risk.

## References

- [Accessibility](references/accessibility.md) - consult when building user
  interfaces or user-facing text.
- [Coding rules](references/coding-rules.md) - consult when writing or changing
  code.
