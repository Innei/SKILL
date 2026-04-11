---
name: generate-design-md
description: >
  Generate a DESIGN.md file for any brand or website by analyzing its visual design system.
  Use when the user asks to "generate a DESIGN.md for [brand/URL]", "create a design system doc for [site]",
  "extract the design tokens from [URL]", or "make a DESIGN.md like [brand]".
  Triggers on any request to document a website's design language in DESIGN.md format.
metadata:
  version: '1.0.0'
argument-hint: <brand-name-or-url>
---

# Generate DESIGN.md

You are a world-class design systems engineer and visual analyst. Your task is to produce a
complete, accurate `DESIGN.md` for a given brand or website, following the exact format used
by the [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) repository.

## Input

The user provides a brand name or URL. If only a brand name is given, infer the canonical
marketing website URL (e.g. "Stripe" → `https://stripe.com`).

## Workflow

### Step 1 — Research the Website

Fetch the website's HTML source and CSS to extract design tokens. Do all of the following:

1. **Fetch the homepage HTML** using `web_fetch` on the primary URL.
2. **Find stylesheet URLs** in the HTML (`<link rel="stylesheet">` tags) and fetch the most
   significant CSS file(s) — especially any that contain CSS custom properties (`:root { --... }`).
3. **Look for font declarations** — `@font-face`, Google Fonts imports, Typekit/Adobe Fonts,
   or references to custom font files. Note the `font-family` name, weights loaded, and any
   `font-feature-settings` values.
4. **Extract CSS custom properties**: scan for `--color-*`, `--font-*`, `--shadow-*`,
   `--radius-*`, `--spacing-*` tokens and their values.
5. **Inspect component patterns**: look for button classes, card classes, nav classes,
   and their CSS values (background, color, padding, border-radius, box-shadow, font-weight).
6. **Note meta signals**: page `<title>`, OG image, brand colors in SVG logos, any inline
   `style` attributes on hero elements.

If the site uses JavaScript-rendered content that prevents full CSS extraction, fetch any
publicly available design system documentation, Storybook, Figma community files, or brand
guidelines pages mentioned on the site.

### Step 2 — Analyze & Synthesize

Map your findings to the 9 sections of the DESIGN.md format. For each section:

- **Section 1**: Identify the dominant background(s), primary typeface and its most distinctive
  properties, the single most memorable visual "signature", and how the accent color is deployed.
  Write in an editorial tone — evocative but grounded in exact hex/px values.

- **Section 2**: Organize colors into semantic sub-groups. Required groups:
  `Primary`, `Interactive`, `Neutral Scale`, `Surface & Borders`, `Shadow Colors`.
  Add brand-specific groups as needed. Every hex value must be real — never invented.

- **Section 3**: Build the full typography hierarchy table (minimum 10 rows). Use the exact
  format: `Xpx (X.XXrem)` for size, numeric weights (300/400/510/600, not "bold"), line-height
  as a ratio with descriptor `(tight)` / `(relaxed)` when applicable, and letter-spacing in px.

- **Section 4**: Document every button variant with full CSS specs. Always include: primary,
  secondary/ghost, pill/badge. Add 1–3 brand-specific distinctive components.

- **Section 5**: State the base spacing unit (usually 8px). List the actual spacing scale values
  found in CSS. Write Whitespace Philosophy as named paragraphs with bold headings.

- **Section 6**: Write the full CSS `box-shadow` value (never a description) in the Treatment
  column. End with the Focus (Accessibility) row. Write 2–3 sentences in Shadow Philosophy.

- **Section 7**: Write ≥6 Do's and ≥6 Don'ts. Every rule must reference a specific token,
  px value, or CSS property — no vague rules like "keep it minimal".

- **Section 8**: Include ≥4 breakpoints. Document actual responsive behavior observed on the
  live site. Note any unusual touch target sizes or collapsing patterns.

- **Section 9**: Write 5 fully self-contained Example Component Prompts — every value must be
  spelled out inline (hex codes, px, weight, radius, shadow) with no references to "the colors
  above". Write 6–8 Iteration Guide rules in priority order.

### Step 3 — Write the DESIGN.md

Output the complete `DESIGN.md` following this **exact document structure**:

```
# Design System Inspiration of [Brand Name]

## 1. Visual Theme & Atmosphere
## 2. Color Palette & Roles
## 3. Typography Rules
## 4. Component Stylings
## 5. Layout Principles
## 6. Depth & Elevation
## 7. Do's and Don'ts
## 8. Responsive Behavior
## 9. Agent Prompt Guide
```

### Step 4 — Save the File

Determine the output location:

- **If run inside the `awesome-design-md` repository** (i.e. `design-md/` directory exists):
  Save to `design-md/[brand-slug]/DESIGN.md`.
  The slug is lowercase, hyphens for spaces, dots kept for domain-style names
  (e.g. `linear.app`, `mistral.ai`, `x.ai`).

- **If run in any other project**:
  Save to `DESIGN.md` in the current working directory.

After saving, report the output path and a 2-sentence summary of the brand's most distinctive
design characteristics.

---

## Format Reference

Study the spec from the `./TEMPLATE.md` if available, or follow
these non-negotiable format rules:

### Color entries

```
- **Name** (`#XXXXXX`): CSS variable if known. 1-sentence role.
- **Name** (`rgba(R,G,B,A)`): Role description.
```

### Typography table columns (in order)

`Role | Font | Size | Weight | Line Height | Letter Spacing | Notes`

- Size: always `Xpx (X.XXrem)`
- Weight: always numeric (`300`, `400`, `510`, `600`) — never "semibold", "bold"
- Line Height: ratio + optional descriptor: `1.07 (tight)`, `1.50`, `1.80 (relaxed)`
- Letter Spacing: `normal` or `−X.XXpx`

### Elevation table columns (in order)

`Level | Treatment | Use`

- Treatment for Level 1+: full CSS `box-shadow` value, e.g.
  `rgba(0,0,0,0.08) 0px 0px 0px 1px`
- Always end with: `Focus (Accessibility) | 2px solid #XXXXXX outline | Keyboard focus`

### Component button sub-sections

Use bold text as the variant heading — NOT a `###` heading:

```
**Primary Blue**
- Background: `#XXXXXX`
- Text: `#XXXXXX`
...
```

### Agent Prompt Guide — Example Component Prompts

Every prompt must be a single quoted string with ALL values inline:

```
- "Create a hero section on white background. Headline at 48px Geist weight 600,
   line-height 1.00, letter-spacing -2.4px, color #171717..."
```

No cross-references like "use the brand purple from Section 2". All values must be explicit.

---

## Quality Standards

A valid DESIGN.md must pass all of these checks:

- [ ] All 9 sections present and numbered correctly
- [ ] Section 1 has ≥7 Key Characteristics bullets (each with at least one concrete value)
- [ ] Section 2 has ≥15 named colors; every shadow rgba is named in `Shadow Colors`
- [ ] Section 3 typography table has ≥10 rows; sizes in dual format `Xpx (X.XXrem)`
- [ ] Section 4 has ≥2 button variants + cards + nav + inputs + ≥1 badge
- [ ] Section 5 includes spacing base unit + key scale + Whitespace Philosophy paragraphs
- [ ] Section 6 elevation table has ≥4 rows; Treatment column has full CSS shadow values
- [ ] Section 7 has ≥6 Do's and ≥6 Don'ts; each is actionable with a specific value
- [ ] Section 8 has ≥4 breakpoints + Collapsing Strategy + Image Behavior
- [ ] Section 9 has ≥5 self-contained prompts + ≥6 Iteration Guide rules
- [ ] No hex values are invented — all come from real CSS on the site
- [ ] No vague language without a concrete supporting value
