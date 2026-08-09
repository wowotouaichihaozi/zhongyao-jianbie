---
name: oh-my-ppt-source-reading
description: Source-document reading workflow for Oh My PPT. Read before generating slides from reference documents or retrieved snippets.
---

# Oh My PPT Source Reading

## Boundary

Use this skill only when the host prompt already provides source documents or source snippets.

Do not discover, infer, or guess source document paths. Use only the `sourceDocumentPaths` explicitly provided by the host prompt. If no source document path is provided, do not scan the project looking for one.

## When to use

- `sourceDocumentPaths` are present.
- Retrieved source snippets are present.
- The task asks to preserve facts, metrics, terminology, conclusions, or page points from a reference document.
- A slide outline appears to come from a parsed reference document.

## When not to use

- No source document path or source snippet is provided.
- The task is a pure visual/style edit that does not use source facts.
- The task is only about layout, animation, or chart mechanics with already supplied data.

## Reading workflow

1. Treat retrieved snippets as an index into the source, not as final evidence.
2. Extract search terms from the current slide title, content points, user instruction, snippets, and any known entities/metrics.
3. Use the DeepAgents filesystem tool `grep(pattern, path, glob)` inside the provided `sourceDocumentPaths` to locate relevant headings, paragraphs, tables, dates, metrics, entities, and terminology. `pattern` is a literal string, not a shell regex; call `grep` multiple times for multiple search terms.
4. Use the DeepAgents filesystem tool `glob(pattern, path)` only if the provided path points to a directory or the host prompt explicitly says multiple matching source files may exist.
5. Use `read_file` only on targeted sections or line ranges found by snippets/grep. Do not read an entire long document into context at once.
6. If the initial grep/read did not yield enough source-grounded evidence, refine search terms and repeat grep -> targeted read. Try synonyms, broader or narrower scope, adjacent section headings, and known entities/metrics.
7. Build slide content only from inspected snippets and targeted source passages.
8. If the needed evidence is still missing after reasonable attempts, omit the unsupported claim or state uncertainty in neutral terms. Do not fill gaps with plausible-sounding content.

### Example

Slide title: "Q3 Revenue Highlights"
Content points: "YoY growth rate", "top product contribution", "regional breakdown"

1. Snippet mentions "revenue grew 15% YoY" -> search terms: `revenue`, `15%`, `YoY`, `Q3`.
2. Call `grep(pattern="revenue", path="/source.md")`, then `grep(pattern="15%", path="/source.md")`, then `grep(pattern="Q3", path="/source.md")` -> matches near the Q3 finance section and regional table.
3. Call `read_file(path="/source.md", offset=118, limit=60)` only around those matches -> confirms the exact growth and regional values.
4. Build the slide with confirmed facts; omit "top product contribution" if no inspected source passage supports it.

## Evidence rules

- Preserve source terminology, product names, system names, roles, dates, metrics, conclusions, risks, decisions, and examples.
- Use only source facts relevant to the current slide. Do not move material for other slides into this slide.
- Do not invent exact facts, metrics, dates, system names, status claims, examples, risks, decisions, or conclusions.
- If a retrieved snippet conflicts with the source passage you inspected, trust the inspected source passage over the snippet.
- If the source conflicts with the page outline, follow the source facts. If the source conflicts with an explicit user instruction, follow the user instruction but avoid unsupported source claims.

## Long-document discipline

- Read nearby sections progressively rather than large ranges. Prefer 50-80 lines around grep matches; avoid reading 200+ lines in a single call unless the section itself requires it.
- Keep notes mentally scoped to the current slide.
- Stop reading once the current slide has enough source-grounded evidence.
- Never use source snippets for one slide as evidence for another slide unless the source passage directly matches that other slide.

## Output discipline

- Do not rewrite the reference document into a generic storyline, marketing narrative, consulting framework, or inspirational theme unless the user explicitly asks for that transformation.
- Slide text should be concise and presentation-ready, but still traceable to source evidence.
- Compress long source passages; do not paste long verbatim excerpts.
- Preserve exact numbers and names only when they appear in the source passage you inspected.
- For charts/tables, use only source-backed labels and values. If exact values are unavailable, use qualitative wording instead of invented numbers.
