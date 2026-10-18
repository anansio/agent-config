---
name: git-workflow
description: This skill should be used when making commits, branching, or preparing changes for review, to keep history clean and focused.
---

# Git Workflow

- Follow [Conventional Commits](https://www.conventionalcommits.org) for commit
  messages: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, and so on.
  Versioning is derived from these types, so use them correctly.
- Use a concise subject in the imperative mood, then explain the reason in the
  body when it is not obvious.
- Make small, focused commits. One logical change per commit.
- Commit code together with its tests and documentation when they belong to the
  same change.
- Do not commit generated files, secrets, or local environment files.
- Never push directly to the main branch. Use a branch and a pull request.
