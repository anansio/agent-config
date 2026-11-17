# Logging

Log features, fixes, and decisions, not every step.

Use the work-log tools (`log_append`, `log_update`, `log_delete`, `log_search`)
whenever the client provides them; they are the log. If they are not available,
skip the log instead of writing files by hand, and do not report a log entry
that was never written.

Keep entries short. Rewrite or delete entries a later change makes obsolete.
