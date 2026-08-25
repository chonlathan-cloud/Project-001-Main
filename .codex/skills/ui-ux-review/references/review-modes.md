# UI/UX Review Modes

Use only the mode relevant to the request. Keep the output concise, prioritized, and tied to inspected evidence.

## Critique Mode

Do not modify code. Use these headings exactly:

### Primary user task

State the user, task, success condition, and important device or workflow context.

### Visual anchor

Identify what currently dominates and what should dominate. Explain any mismatch.

### Critical UX issues

List only issues that materially affect task completion, comprehension, safety, recovery, or action priority. Distinguish missing evidence from confirmed defects.

### Visual hierarchy issues

Cover hierarchy, density, typography, spacing, alignment, composition, contrast, and consistency. Prioritize structural issues over polish.

### AI-generated patterns detected

Name the specific pattern, cite the affected element or component, and explain why it weakens this product experience. Do not label ordinary reuse as generic without evidence.

### Recommended changes

Prefix every recommendation with exactly one action label:

- `REMOVE` — eliminate content or decoration without sufficient product value.
- `MERGE` — combine redundant or fragmented information or controls.
- `MOVE` — change sequence, grouping, or placement.
- `REDUCE` — lower visual weight, quantity, spacing, copy, or decoration.
- `EMPHASIZE` — strengthen the true task, state, information, or action anchor.
- `REPLACE` — substitute a pattern that conflicts with the task or design system.
- `KEEP` — explicitly preserve a strong existing decision at risk of unnecessary redesign.

For each item, give the reason and expected UX effect. Rank recommendations by impact and prefer fewer decisive changes.

## Implementation Plan Mode

Do not modify code. Require an approved critique or clearly supplied decisions; if approval is unclear, identify the unresolved decisions instead of inventing a redesign.

Start with the intended outcome and invariants to preserve. For every planned change specify:

- critique decision and expected outcome;
- affected files and components;
- existing components, tokens, or patterns to reuse;
- layout and content-hierarchy changes;
- desktop, tablet, mobile, and relevant LINE webview implications;
- semantic HTML, keyboard, focus, labeling, contrast, and reduced-motion implications;
- implementation risks, behavior-preservation risks, and validation method.

Order work into independently verifiable steps. Explicitly state that backend/API/business logic, authentication, authorization, domain models, validations, and state transitions remain unchanged. Flag any recommendation that cannot be implemented without crossing that boundary and request explicit permission rather than including it silently.

Include a focused verification checklist covering lint/build, representative viewport widths, key page states, keyboard flow, and regression checks for shared components.

## Final Review Mode

Review the implementation rather than the plan. Inspect the final code and, when feasible, the rendered page at representative desktop, tablet, and mobile widths and relevant loading, empty, error, success, disabled, and permission states. State which evidence was unavailable.

Report:

- Visual hierarchy: `N/10`
- Information density: `N/10`
- Interaction clarity: `N/10`
- Design-system consistency: `N/10`
- Responsive UX: `N/10`
- Accessibility: `N/10`
- Product-specific character: `N/10`
- AI-template smell: `LOW`, `MEDIUM`, or `HIGH`

Use `10` only when no meaningful issue remains in that dimension. Base scores on observable evidence, not implementation effort.

Then explain:

1. what improved and should remain;
2. remaining issues, ordered by user impact;
3. regressions or unverified risks;
4. the smallest next changes needed.

Do not approve the UI when AI-template smell is `HIGH`. When it is `MEDIUM`, approval must be qualified with the concrete issues preventing `LOW`.
