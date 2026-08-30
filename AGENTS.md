# Project Working Rules

These rules apply to the entire repository.

## Non-negotiable safety rules

- Work only inside this repository. Do not modify the exported submission copies, backup directories, or any project outside this repository.
- Never delete a file or directory. If something must be retired or reorganized, move it to an explicitly named archive location inside the repository and record the move in the optimization tracker.
- Never run recursive deletion or cleanup commands, including `rm -rf`, `Remove-Item -Recurse`, `rmdir /s`, `git clean`, or equivalent commands and scripts.
- Do not use destructive Git commands such as `git reset --hard` or `git checkout --`.
- Preserve user-created and untracked files. In particular, never stage or expose `.env` files, credentials, tokens, or private runtime data.

## Required workflow

1. Inspect the affected implementation before changing code.
2. Keep each phase small enough to review and verify independently.
3. For user-facing frontend changes, verify the actual route at desktop widths, including loading, empty, error, populated, and interactive states that apply.
4. Build without cleaning output directories. Use a non-destructive build option such as `npm run build -- --emptyOutDir=false`; never invoke a clean script.
5. For material feature, API, architecture, or deployment changes, update the root `README.md` with the user-visible behavior and verification command.
6. Before committing, inspect `git diff`, run the relevant checks, and stage only intentional source/documentation files. Never stage credentials or private runtime data.

## Commit policy

- A phase may be committed after its relevant build/tests and browser checks pass.
- Use focused commit messages and keep unrelated user changes out of the commit.
- Pushing is allowed only to the configured private project remote and only after the local commit is verified.
