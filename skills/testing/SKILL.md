---
name: testing
description: This skill should be used when writing or running tests, or when a change needs verification, to keep code covered and tests meaningful.
---

# Testing

- Cover new behaviour with tests before calling a change done.
- Test real code paths. Avoid mocks unless they are strictly necessary, and
  justify them when you use them.
- Prefer small, deterministic tests over large end-to-end setups when a smaller
  test proves the same thing.
- Run the relevant tests locally before finishing.

## References

- [Java testing](references/java-test.md) - consult when writing Java tests.
