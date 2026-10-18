# Coding Rules

## Avoid overengineering

- Solve the problem in front of you, not imagined future needs.
- Prefer the smallest solution that fully meets the requirement. A simple,
  pragmatic solution beats an exhaustive one.
- Add an abstraction only when there is a second real use for it.
- Keep changes focused. Do not refactor code that is unrelated to the task.

## Production-ready

- Ship finished code. Leave no dummy code, placeholders, or stray TODO markers.
- If a gap is intentional, state it as a clear, tracked item, not as a comment
  left behind in the code.

## Compatibility

- Do not keep a fallback or a compatibility path for every change. Keep the
  code clean and minimal under one maintainable design; the process as a whole
  need not stay backward compatible.
- Warn when a change breaks compatibility for a version already in use, and
  offer the choice with short options: keep compatibility, or drop it.

## Safe and tested

- Write code that is secure by default. Validate input at the boundaries.
- Cover new behaviour with tests. A change without tests is not done.
- Comment every test. Say what the test verifies and why it matters, so the
  intent survives without reading the implementation.
