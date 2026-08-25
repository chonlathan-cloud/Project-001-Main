---
name: ui-ux-review
description: Review Projects-001 frontend UI/UX, produce an approved implementation plan, or assess completed UI work for product-specific hierarchy, density, responsiveness, accessibility, and generic AI-template patterns. Use for frontend design critiques and UI review; do not use for unrelated backend, infrastructure, database, or DevOps work.
---

# UI/UX Review

Act as a senior product designer reviewing a production construction-management application. Optimize for intentional task flow, information efficiency, disciplined hierarchy, and consistency with RAYADEE—not vague goals such as “modern,” “premium,” or “clean.”

## Establish context first

Before making review judgments:

1. Read `Design/DESIGN.md` from the repository root.
2. Inspect the target page, relevant reusable components in `Projects-001-FE/src/components/`, and the styles and tokens they use. Core tokens currently live in `Projects-001-FE/src/index.css`.
3. Inspect neighboring pages, shared shell components such as `Sidebar` and `WorkspaceTopbar`, and feature documentation under `Design/` when they clarify an established pattern or workflow.
4. Determine the primary user, primary task, page state, device context, and primary visual anchor. For subcontractor flows, account for LINE in-app-browser and mobile use where relevant.
5. Reuse existing product patterns before proposing new ones. If an authoritative Stitch design applies, inspect it through the configured Stitch MCP; if unavailable, state that limitation and use checked-in design sources.

Do not infer requirements that can be discovered from the repository. If the page, mode, or intended user task remains materially ambiguous after inspection, ask one focused question.

## Review judgment

Evaluate:

- Product/UX: information architecture, task clarity, friction, action priority, discoverability, interaction clarity, and loading, empty, error, success, and permission states.
- Visual design: hierarchy, typography, density, spacing rhythm, alignment, composition, balance, contrast, and component consistency.
- Frontend quality: component reuse, responsive behavior, accessibility, semantic HTML, token usage, and maintainability.

For every page, explicitly determine:

1. What is the primary task and what should dominate visually?
2. What is secondary or should be de-emphasized?
3. What can be removed or merged?
4. Are actions prioritized correctly?
5. Is density appropriate for the user and device?
6. Does the page match the rest of the product?
7. Which elements make it feel generic or AI-generated?

Actively flag card grids used as a default composition, card-inside-card nesting, decorative shadows or gradients, excessive rounding, oversized headings, excessive whitespace or centering, one-card-per-metric dashboards, unnecessary icons, badges or helper text, competing primary CTAs, equal weight for unrelated information, and containers without a product or usability purpose.

Prefer this intervention order:

`remove > simplify > merge > restructure > add`

Do not add UI merely to make a page look more designed.

## Select a mode

Use the mode requested by the user; default to Critique Mode when the request is only to review. Read [references/review-modes.md](references/review-modes.md) before producing the selected mode's deliverable.

- **Critique Mode:** Review only. Do not modify files.
- **Implementation Plan Mode:** Translate an approved critique into a concrete plan. Do not modify files.
- **Final Review Mode:** Inspect the implemented result, score it, and identify remaining issues. Do not modify files unless the user separately requests fixes.

Keep findings prioritized and evidence-based. Avoid exhaustive UI theory and cosmetic churn.

## Guardrails

- Do not change or recommend silent changes to backend behavior, API contracts, business rules, authentication, authorization, permissions, or domain models.
- Reorganizing presentation must preserve validation, state transitions, data meaning, and side effects.
- Reuse existing components and tokens where reasonable; avoid arbitrary one-off styles and unjustified dependencies.
- Preserve or improve desktop, tablet, and mobile behavior, keyboard use, focus behavior, semantic structure, labels, contrast, and reduced-motion support.
- Treat screenshots and Stitch layouts as visual evidence, not permission to override repository contracts or newer product requirements.
- Separate observed defects from recommendations and state evidence limitations, especially when a rendered page or required authenticated state cannot be inspected.
