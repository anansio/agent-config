# Coding Rules

## Avoid overengineering

Solve the problem in front of you, not imaginary future ones. Prefer the
smallest solution that fully works; simple and a little pragmatic beats complete
and complex. Add an abstraction only when there is a second real use for it.
Keep the change focused, and leave unrelated code alone.

## Production-ready

Ship finished code. No dummy code, no placeholders, no leftover TODOs. If you
deliberately leave a gap, say so openly instead of hiding it in a comment.

## Compatibility

Not every change needs a fallback or a compatibility path; keep the code clean
under one design. The project as a whole does not have to stay backward
compatible. But when a change breaks a version that is already in use, say so
and offer the choice: keep compatibility, or drop it.

## Safe and tested

Write secure code and check input where it enters. Cover new behavior with
tests; a change without tests is not done. Comment each test with what it
checks and why, so the intent survives.
