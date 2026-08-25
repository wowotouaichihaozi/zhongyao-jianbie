---
name: safe-archive-workspace
description: Safely inspect and extract ZIP archives uploaded into the current DeepSeek Harness workspace.
---

# Safe Archive Workspace

Use the already extracted directory reported next to an uploaded ZIP whenever it is available.

If a ZIP still needs extraction, run `scripts/safe_extract_zip.py` with an archive path and a new output directory under `.dsh-attachments/extracted/`. Never call `unzip`, never extract outside the current workspace, and never execute files from an archive.

The extractor rejects absolute paths, parent traversal, symbolic links, encrypted entries, duplicate targets, more than 2,000 entries, files larger than 128 MiB, total expansion above 512 MiB, and suspicious compression ratios.

After extraction, inspect only the files relevant to the user's request. Do not recursively delete uploaded archives or extracted directories.
