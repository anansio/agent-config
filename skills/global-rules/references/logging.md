# Logging

Log features, fixes, and decisions, not every step.

Use the work-log tools (`log_append`, `log_update`, `log_delete`, `log_search`)
whenever the client provides them; they are the log. If they are not available,
skip the log instead of writing files by hand, and do not report a log entry
that was never written.

Pass `project_dir` with the directory you are working in on every call. The
server runs next to the plugin and cannot see your project, so without it the
entry lands in the plugin install instead of the project. Pass the same
`project_dir` to `log_update`, `log_delete`, and `log_search`, or they will look
in the wrong file.

Keep entries short. Rewrite or delete entries a later change makes obsolete.
