# Project Working Rules

These rules apply to the entire repository.

## Non-negotiable safety rules

- Work only inside this repository. Do not modify the exported submission copies, backup directories, or any project outside this repository.
- Never delete a file or directory. If something must be retired or reorganized, move it to an explicitly named archive location inside the repository and record the move in the optimization tracker.
- Never run recursive deletion or cleanup commands, including `rm -rf`, `Remove-Item -Recurse`, `rmdir /s`, `git clean`, or equivalent commands and scripts.
- Do not use destructive Git commands such as `git reset --hard` or `git checkout --`.
- Preserve user-created and untracked files. In particular, never stage or expose `.env` files, credentials, tokens, or private runtime data.

## Required workflow

1. Read the official A3 scoring requirements and inspect the affected implementation before changing code.
2. Keep `docs/A3-scoring-optimization-tracker.md` current. Before a change, mark the item in progress; after verification, record what is complete, what remains, and the evidence.
3. Keep each phase small enough to review and verify independently.
4. For user-facing frontend changes, verify the actual route at desktop and mobile widths, including loading, empty, error, populated, and interactive states that apply.
5. Build without cleaning output directories. Use a non-destructive build option such as `npm run build -- --emptyOutDir=false`; never invoke a clean script.
6. For material feature, API, architecture, or deployment changes, update the root `README.md` with the user-visible behavior and verification command.
7. Before committing, inspect `git diff`, run the relevant checks, update the tracker, and stage only intentional source/documentation files. Never stage environment files.

## A3 product and UI standards

- Preserve the complete learning loop: profile collection and update, profile-driven path planning, multimodal resource generation, learning verification, feedback/tutoring, effect assessment, and path adjustment.
- Keep at least six updateable profile dimensions and at least five distinct resource types visibly demonstrable.
- Make profile dependence, multi-agent collaboration, source grounding, safety review, structured validation, and long-running task progress visible to judges where relevant.
- Secondary and deeper pages must retain clear hierarchy, navigation context, consistent spacing and typography, accessible controls, responsive layout, and useful loading/empty/error states.
- Use the existing Vue patterns, design tokens, and Lucide icon library. Avoid nested decorative cards, oversized marketing headings, one-color page treatments, and text-only substitutes for familiar tool icons.
- Do not claim capabilities or evidence that the running system cannot demonstrate.

## Commit policy

- A phase may be committed after its relevant build/tests and browser checks pass.
- Use focused commit messages and keep unrelated user changes out of the commit.
- Pushing is allowed only to the configured private project remote and only after the local commit is verified.
