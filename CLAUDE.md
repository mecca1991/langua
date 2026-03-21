## Git Commit Rules

- Always commit using the email `yekuwilfred@gmail.com`
- Configure git locally if needed: `git config user.email "yekuwilfred@gmail.com"`
- Never add `Co-Authored-By` trailers to commit messages
- Commit messages should contain only the subject line (and optional body) — no attribution footers

## Execution Rules

- Do exactly what was asked. Do not widen scope without explicit approval.
- Start by inspecting the existing codebase and relevant files before proposing changes.
- Prefer small, targeted edits over refactors or rewrites.
- Do not introduce new abstractions, dependencies, or file moves unless they are required to complete the task.
- If the request is ambiguous, choose the safest narrow interpretation and state the assumption briefly.
- Do not derail into brainstorming, architecture discussions, or optional improvements unless asked.
- When fixing a bug, address the root cause in the current code path before suggesting broader cleanup.
- Preserve existing patterns unless they clearly prevent the requested change.
- Never overwrite or revert user changes you did not make.
- Validate the result with the most direct available check, then report what was verified and what was not.
- If you hit a blocker, stop and surface the blocker clearly instead of improvising unrelated changes.
- Keep responses concise and implementation-focused.
