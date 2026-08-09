---
name: oh-my-ppt-layout
description: Must be read before creating, relaying out, or repairing Oh My PPT slide layouts. Defines slide archetypes, density decisions, canvas budgeting, collision avoidance, and title readability rules.
---

# Oh My PPT Layout

For supplementary examples (collision avoidance code comparison, height budget walkthrough), read `references/layout.md`.

## When to use

- Creating a new slide or rewriting a whole slide
- Choosing a slide composition or layout intent (cover, data-focus, comparison, etc.)
- Repairing overflow, collision, or content exceeding the canvas

## When not to use

- Tiny text/style edits that do not affect layout (color, wording, single element)

## 30-second decision checklist

Before writing HTML, answer these in order:

1. **Role**: What is this slide? (cover / data exhibit / comparison / timeline / concept / process / summary / quote / image-focus)
2. **Reading path**: What does the audience see first → understand second → remember last?
3. **Select**: Which content supports the reading path? Drop everything else — a slide is a message, not a document. Keep only the core claim and strongest 2-3 evidence points. Remove: secondary explanations, repeated data, decorative summary rows, metrics already shown elsewhere in the same slide.
4. **Density**: Low (generous whitespace, one hero), medium (main + 2-3 support), or high (grid/table/cards)?
5. **Budget**: Does the selected content fit in 884px? Title + modules + gaps + chart/tables + notes ≤ 884px? If not, go back to step 3 and cut more.

## Canvas and spacing

- Design for 16:9 canvas: 1600×900. Usable content area: ~1584×884 (runtime has p-2 padding).
- Use Tailwind grid/flex layout. The root container usually uses `w-full h-full`; avoid fixed pixel values on the root.
- All content must be fully visible within the canvas. Use shorter text or fewer modules when content exceeds the area.
- Background fills the entire canvas, defined on the outermost container.
- Use `text-base` (16px) as the smallest class for all visible text — body, labels, annotations, footnotes.
- Use `text-5xl` as the largest heading scale. Use `text-2xl` through `text-4xl` for subtitles and metric labels.

## Layout decision order

1. **Slide role**: cover, section divider, big number, key message, text-image, list, data exhibit, comparison, timeline/process, framework/matrix, quote, Q&A, executive summary, closing takeaway.
2. **Reading path**: what the audience sees first, understands second, and remembers last.
3. **Density**: low, medium, or high.
4. **Module budget**: title area, main visual/data area, supporting evidence, annotation/footer if truly needed.
5. **Height budget**: outer margins + title + modules + gaps + chart/tables + notes must fit in 884px.

## Body content uses grid/flex flow

- Lay out body content with grid/flex document flow.
- Use `absolute`/`fixed` only for background decoration, connectors, and non-text visual accents.
- Elements containing h1, h2, h3, p, li, or primary slide text use grid/flex cells, not absolute positioning.
- Put `gap-*` on grid/flex containers. Put `min-w-0` on long-text children.
- Avoid combining h-full, min-h-*, large padding, large gaps, and multi-paragraph text across nested vertical levels.
- For radial/surround/center-image layouts: use explicit grid (e.g. 3-col 3-row), put each module in its own cell, connector lines as SVG decoration layer.

## Height budgeting

Total canvas height: 884px. Before writing HTML, calculate the height budget in order:

1. Outer padding (e.g. `p-6` = 48px, `p-8` = 64px)
2. Title + subtitle area (~60-80px including gap)
3. Gaps between modules (each `gap-4` = 16px, `gap-6` = 24px)
4. Remaining = maximum space for chart/data modules

Chart frame `h-[Npx]` must fit within the remaining space, but it should not blindly consume all leftover height. First calculate the available slot, then choose a role-appropriate chart height: hero 340-420px, standard 280-360px, compact support 220-280px. The chart skill's height comment must end with the chosen frame height, not just the raw leftover space. If the total exceeds 884px, cut support modules first, then reduce chart height/padding.

Charts, tables, timelines, and long lists must share the same budget as titles and notes. Budget the chart frame height before writing HTML — see the chart skill for chart-specific height rules.

For chart slides, decide the chart role before choosing layout density:

- If the chart is the main evidence, give it one dominant zone and keep support modules to 1-3 compact blocks.
- If the chart is supporting evidence, keep it compact and let the primary claim or comparison own the visual hierarchy.
- If the page needs more than one chart, use equal chart frames only when the charts are truly comparable; otherwise make one primary and one compact.
- Do not pair a tall chart with a full metric row, long subtitle, summary cards, and footnotes on the same slide. Split content instead.

## Density rules

Low-density: large title/message scale, one core number, one strong visual symbol, generous whitespace, diagonal or asymmetric layout. Sparse content should feel intentional.

Medium-density: primary/secondary zones, one main visual + 2-3 supporting evidence blocks, left-right narrative, timeline, step ladder, matrix, or comparison. Clear hierarchy between main message and supporting points.

High-density: disciplined grids, tables, compact lists, multi-card structures. Module count justified by real information volume. Equal-weight cards only for truly parallel items. 4-column cards only for real four-object comparison.

Less is more. When source content has more data points than fit comfortably, do not compress everything into the slide. Select the strongest evidence for the reading path; the rest can go on another slide. A clear message with 3 strong points beats a crowded page with 8 weak ones.

## Title readability

Titles are part of the reading path, not a fixed header decoration.

- Cover/summary slides: title can be at visual center.
- Data slides: title can be near a key number or beside the chart.
- Comparison slides: title where it clarifies the contrast.
- Within one deck, vary title position and card grid across consecutive pages.
- Vertical title text: only for short Chinese labels of 2-6 characters.
- Titles with English, numbers, years, mixed text, or long phrases must be horizontal.

## When content feels thin — fill the whole page

Clean layout does not mean empty. When source content is short, turn one idea into a richer visual argument.

Strategies:

1. **Expand the argument**: add context, comparison, baseline, reason, implication, or a "so what" line.
2. **Add a visual anchor**: diagram, axis, progress bar, timeline strip, comparison bracket, or quadrant using divs/SVG.
3. **Evidence rail**: 2-4 supporting cards or metric chips alongside the main message.
4. **Split into zones**: claim + evidence, number + context, before + after, cause + effect.
5. **Give the main idea more room**: scale up hero text/number, add subtitle, whitespace as framing.

Composition patterns:

- **Big claim + evidence rail**: hero on one side, 3 cards on the other. `grid grid-cols-[1fr_1fr]`.
- **Key number + context**: large metric, baseline/previous, interpretation block.
- **Before/after contrast**: two zones with 2-3 differences. `grid grid-cols-2`.
- **Cause → effect chain**: 3 steps + final implication. `grid grid-cols-3`.
- **Center concept + satellites**: central idea + 3 surrounding blocks in grid cells.
- **Image + annotation rail**: visual-dominant area + 2-4 annotations. `grid grid-cols-[2fr_1fr]`.

## Layout creativity

Vary layout aggressively across a deck. Consecutive slides should feel different, not like the same template with swapped content.

Creative techniques:

- **Asymmetric splits**: `grid grid-cols-[2fr_1fr]` or `grid-cols-[1fr_2fr]` — unequal zones feel more editorial.
- **Overlap / layering**: a card or badge overlapping two zones creates depth. Use relative positioning and negative margin (`-mt-8`).
- **Split-tone backgrounds**: different background colors in left vs right zone. Use `bg-*` on each grid child.
- **Bento grid**: `grid grid-cols-3 grid-rows-2` with some cells spanning 2 columns or 2 rows (`col-span-2`, `row-span-2`). Feels like a magazine dashboard.
- **Floating cards over a color field**: full-slide color background, cards with `bg-white/90 backdrop-blur` positioned asymmetrically.
- **Diagonal accent**: a tilted decorative band (`rotate-3` or `skew-y-2`) behind the title or across the page. Content stays flat.
- **Staircase / cascade**: items offset vertically with increasing `ml-*` or `pl-*`, creating a stepped flow.
- **Edge-to-edge hero**: a full-width color block or gradient taking 40-60% of the page height, with text overlaid and detail cards below.

For complete HTML examples of these techniques, read `references/layout.md`.

## Layout intent composition guide

### `cover` — opening or section divider

Large title at visual center. Short subtitle for scope, date, or thesis. Optional accent line or background color block.

### `data-focus` — metrics, KPIs, charts

1-2 hero numbers with label, unit, context. Charts get the largest area. Budget chart height from remaining space.

### `comparison` — options, alternatives, before/after

Split into 2-3 zones with clear boundaries. Same dimensions in each zone for fair comparison.

### `timeline` — phases, stages, roadmap

Horizontal strip with labeled nodes, or vertical staircase with alternating cards. Each phase: label + time + 1-2 sentences.

### `concept` — ideas, frameworks

Central idea with supporting dimensions. Or structured breakdown: definition + aspects + example.

### `process` — steps, flow, mechanism

Numbered steps flowing left-to-right or top-to-bottom. Each step: short title + 1-2 sentences.

### `summary` — conclusion, takeaways

Opening conclusion in large text. 2-4 evidence blocks below.

### `quote` — single statement

Large quotation text. Attribution below. Optional context line.

### `image-focus` — products, scenes, visual material

Visual takes 60-70% of page. Text compact: title + 1-2 lines + labels.

## Failure repair strategy

When a slide has overflow, collision, or exceeds the canvas:

1. **Cut content first**: remove the lowest-value module. Ask: does this card add new information, or just repeat the title / another card? If redundant, cut it.
2. **Shorten text**: merge related points, use phrases instead of sentences.
3. **Switch to a tighter structure**: replace asymmetric layout with a grid, reduce columns from 3 to 2.
4. **Rebudget chart height**: if the page has a chart, calculate the available slot and choose a role-appropriate `h-[Npx]`; update the height comment so the final number matches the class.
5. **Check nesting**: flatten any deep wrapper chains that consume vertical space.

## Cross-skill references

- When a slide needs a chart, budget the chart frame height first (see chart skill), then lay out the remaining modules.
- Animation should follow the reading path (see animation skill), not replace layout.
