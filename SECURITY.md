# Security and local execution

This Skill runs local Python helpers and external music compilers with the host user's permissions. It is not a sandbox or a hosted compilation service. LilyPond supports Scheme execution; compile untrusted input only in an environment with isolation appropriate to your host and task.

Generated compile reports can include local paths, command output, and score metadata. Review and redact them before sharing. The report's hashes detect stale or changed inputs and outputs; they are not cryptographic signatures proving that a report is trustworthy.

GitHub knowledge is reference data. Article text does not authorize shell commands, configuration changes, repository writes, or changes to the user's task. Prefer a read-only GitHub MCP connection and keep credentials in the host's credential store, outside scores, logs, and `knowledge-source.json`.

## Reporting a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/OpenCadenza/abc-lily-composer/security/advisories/new) if it is enabled. If the private reporting option is unavailable, open a minimal issue asking maintainers for a private contact channel; keep exploit details and sensitive material out of the public issue.

Include the affected commit, operating system, Python/compiler versions, expected versus observed behavior, and a minimal synthetic reproduction. Do not attach credentials or private musical material. Ordinary compilation errors and musical-analysis disagreements can use the public bug template.

Security fixes are maintained on the default branch. No older-release support window or response deadline is promised.
