# Design System: Projects-001 Admin Portal (Modern Minimal)

## 1. Visual Identity & Vibe
- **Core Concept:** "Modern Minimal Construction Management" — Clean, spacious, and highly legible for complex data (BOQs, Financials).
- **Personality:** Professional, Earthy, Trustworthy, and Clutter-free.
- **Visual Style:** Flat design with ample whitespace. Use subtle dividing lines instead of heavy drop shadows. Focus on typography to build hierarchy. Optimized for Web and Tablet views (Sidebar navigation).

## 2. Color Palette (Corporate CI)
- **Primary:** `#4f6f64` (Muted Teal) - For primary buttons, active sidebar links, and key highlights.
- **Secondary/Accent:** `#c2a878` (Sand Gold) - For warning states, secondary actions, and subtle highlights.
- **Background:** `#f9f5f2` (Soft Off-White) - Global app background.
- **Surface:** `#ffffff` (Pure White) - For content cards, modals, and tables.
- **Text & High Contrast:** `#2f2e2c` (Charcoal Black) - For all primary text and headings. Soften to `opacity: 0.6` for secondary text.

## 3. Typography
- **Primary Font:** 'Inter' or 'Sarabun' for a clean, modern corporate look.
- **Headings:** Bold, Charcoal (`#2f2e2c`), with tight letter-spacing.
- **Data/Tables:** Use tabular-nums (monospaced numbers) for all financial amounts and BOQ values for easy scanning.

## 4. Component Specs
- **Cards & Modals:** White background (`#ffffff`), `1px` solid border (`#f9f5f2` darkened slightly or `#e2e8f0`), Border-radius: `12px`. Subtle shadow only on hover.
- **Buttons:** - Primary: Solid `#4f6f64`, white text, `8px` radius.
  - Secondary: Outline with `#c2a878` border and text.
- **Data Tables (BOQ & Insights):** Clean tables with plenty of cell padding. Header row gets a very subtle `#f9f5f2` background. No vertical borders, only light horizontal dividers.