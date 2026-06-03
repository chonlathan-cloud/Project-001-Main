---
name: ui-ux-implementation
description: Extracts UI designs from Google Stitch MCP and implements them as React components in the frontend workspace.
---

# UI/UX Component Implementation & Sync

This skill automates the extraction of UI designs from the Google Stitch MCP and implements them as React components in the frontend workspace.

## Intent & Triggers
- **Manual Invocation:** Triggered via `/skills ui-ux-implementation`
- **Use Case:** When a new design is ready in Google Stitch or a UI component needs updating based on new design tokens.

## System Instructions & Persona
Act as the `@ui-ux-engineer` SubAgent.
You must prioritize pixel-perfect implementation, accessibility (a11y), and clean component architecture.

## Context & Repository Awareness
- Target Frontend Directory: `Projects-001-FE/src/`
- Target Design Directory: `Design/`
- Read `Projects-001-FE/package.json` to understand available UI libraries and styling tools.

## Workflow / Step-by-Step Execution

### Phase 1: Design Extraction (MCP Integration)
1. Invoke the `google-stitch` MCP tools to retrieve the target UI component's design tokens, layout hierarchy, and SVG assets.
2. Print a summary of the extracted design properties (colors, typography, spacing).

### Phase 2: Implementation Planning
1. Analyze existing components in `Projects-001-FE/src/components/` to maximize reuse.
2. Propose the component structure (React `.jsx` or `.tsx` files) and styling approach. Wait for user approval if the change is massive.

### Phase 3: Code Generation & Modification
1. Generate the React components.
2. If assets (like SVG icons) are needed, place them in `Projects-001-FE/public/` or `Projects-001-FE/src/assets/`.
3. Wire up the component strictly for UI presentation (use mock props if backend integration is not requested).

## Verification Gate (Constraints)
- **Syntax Check:** Execute `cd Projects-001-FE && npm run lint` (or equivalent ESLint command) to ensure no syntax errors.
- **Build Check:** Execute `cd Projects-001-FE && npm run build` to verify the Vite build succeeds.
- Do not declare the skill complete if there are unresolved React/JSX syntax errors.