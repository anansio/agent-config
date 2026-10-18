---
name: git-workflow
description: Use when committing, branching, or preparing changes for review, to keep history clean and focused.
---

# Git Workflow

- Write commit messages in [Conventional Commits](https://www.conventionalcommits.org)
  style: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`. Versioning
  comes from these types, so get them right.
- Use a short imperative subject, and explain why in the body when it is not
  obvious.
- Keep commits small: one logical change each.
- Keep code, tests, and docs for one change in the same commit.
- Do not commit generated files, secrets, or local environment files.
- Never push to main directly. Use a branch and a pull request.
