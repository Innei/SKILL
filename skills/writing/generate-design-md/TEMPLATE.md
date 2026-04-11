# DESIGN.md Template & Specification

This document defines the canonical format for all `DESIGN.md` files in this repository.
It is both a human-readable spec and a fill-in-the-blanks template.

---

## Template

Copy the block below and replace every `[PLACEHOLDER]` with real values.

---

```markdown
# Design System Inspiration of [Brand Name]

## 1. Visual Theme & Atmosphere

[2–4 paragraphs that describe the overall mood, philosophy, and design sensibility of the brand's site.
Mention: background color strategy, primary typeface and its role, the defining "signature move"
(e.g. shadow-as-border, weight-300 headlines, dark-mode native), and how the accent color is used.
Write in an editorial tone — evocative but specific, with hex values and CSS details inline.]

**Key Characteristics:**
- [Typeface name + its most distinctive property — e.g. custom variable font with OpenType `"ss01"` on all text]
- [Signature typographic choice — e.g. weight 300 at display sizes, aggressive negative letter-spacing (-2.4px)]
- [Background color strategy — e.g. binary light/dark sections, single near-black canvas]
- [Accent color role — e.g. single accent color `#XXXXXX` reserved exclusively for interactive elements]
- [Border / shadow philosophy — e.g. shadow-as-border `0px 0px 0px 1px rgba(0,0,0,0.08)`, whisper borders `1px solid rgba(0,0,0,0.1)`]
- [Radius signature — e.g. pill CTAs (980px radius), conservative 4–8px on all elements]
- [Any other highly distinctive visual element — e.g. macOS-native inset shadow system, gradient stripe punctuation]
- [One more distinguishing pattern or interaction characteristic]

## 2. Color Palette & Roles

### Primary
- **[Color Name]** (`#XXXXXX`): [Token variable if known, e.g. `--color-primary`]. [1-sentence functional role — what it's used for and why it feels that way.]
- **[Color Name]** (`#XXXXXX`): [Role description.]
- **[Color Name]** (`#XXXXXX`): [Role description.]

### [Group Name — e.g. Brand & Dark / Workflow Accents / Secondary]
- **[Color Name]** (`#XXXXXX`): [Role description.]
- **[Color Name]** (`#XXXXXX`): [Role description.]

### Accent Colors
- **[Color Name]** (`#XXXXXX`): [Token variable]. [Role — icon, gradient, alert, etc.]
- **[Color Name]** (`#XXXXXX`): [Role description.]

### Interactive
- **[Color Name]** (`#XXXXXX`): Primary link / CTA color.
- **[Color Name]** (`#XXXXXX`): Hover state — slightly darker/lighter variant.
- **[Color Name]** (`#XXXXXX`): Focus ring color.

### Neutral Scale
- **[Neutral 900]** (`#XXXXXX`): Primary headings, nav text, strong labels.
- **[Neutral 600]** (`#XXXXXX`): Secondary text, description copy.
- **[Neutral 400]** (`#XXXXXX`): Placeholder text, disabled states.
- **[Neutral 100]** (`#XXXXXX`): Borders, dividers, card outlines.
- **[Neutral 50]** (`#XXXXXX`): Subtle surface tint.

### Surface & Borders
- **[Surface Name]** (`#XXXXXX`): [Role — e.g. card background, section alt background.]
- **[Border Name]** (`#XXXXXX` or `rgba(...)`): [Role — e.g. standard divider.]

### Shadow Colors
- **[Shadow Name]** (`rgba(X,X,X,X.XX)`): [Role — e.g. primary branded shadow, ambient overlay.]
- **[Shadow Name]** (`rgba(X,X,X,X.XX)`): [Secondary/layered shadow.]

## 3. Typography Rules

### Font Family
- **Primary**: `[Font Name]`, with fallbacks: `[fallback1, fallback2, ...]`
- **Monospace** *(if used)*: `[Mono Font Name]`, with fallbacks: `[fallback1, ...]`
- **OpenType Features**: `"[feat]"` enabled globally on [font name]; `"tnum"` for tabular numbers on [specific context].

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|------|--------|-------------|----------------|-------|
| Display Hero | [Font] | [Xpx (X.XXrem)] | [weight] | [ratio (descriptor)] | [Xpx or normal] | [Brief note] |
| Display Large | [Font] | [Xpx (X.XXrem)] | [weight] | [ratio] | [Xpx or normal] | |
| Section Heading | [Font] | [Xpx (X.XXrem)] | [weight] | [ratio] | [Xpx or normal] | |
| Sub-heading Large | [Font] | [Xpx (X.XXrem)] | [weight] | [ratio] | [Xpx or normal] | |
| Sub-heading | [Font] | [Xpx (X.XXrem)] | [weight] | [ratio] | [Xpx or normal] | |
| Card Title | [Font] | [Xpx (X.XXrem)] | [weight] | [ratio] | [Xpx or normal] | |
| Body Large | [Font] | [Xpx (X.XXrem)] | [weight] | [ratio (relaxed)] | normal | |
| Body | [Font] | [Xpx (X.XXrem)] | [weight] | [ratio] | normal | Standard reading text |
| Button | [Font] | [Xpx (X.XXrem)] | [weight] | [ratio] | normal | |
| Caption | [Font] | [Xpx (X.XXrem)] | [weight] | [ratio] | normal | |
| Micro | [Font] | [Xpx (X.XXrem)] | [weight] | [ratio] | [Xpx or normal] | |
| Code Body | [Mono Font] | [Xpx (X.XXrem)] | [weight] | [ratio] | normal | Code blocks |

### Principles
- **[Principle name]**: [1–2 sentences explaining the most distinctive typographic decision — e.g. why the brand uses weight 300, how letter-spacing scales with size, OpenType feature strategy.]
- **[Principle name]**: [Weight system — e.g. "Three weights only: 400 (body), 500 (UI), 600 (headings)."]
- **[Principle name]**: [Tracking / letter-spacing rule across the scale.]
- **[Principle name]**: [Any other defining principle — optical sizing, line-height range, mono usage.]

## 4. Component Stylings

### Buttons

**[Primary Variant Name — e.g. Primary Blue, Primary Dark]**
- Background: `#XXXXXX`
- Text: `#XXXXXX`
- Padding: `Xpx Xpx`
- Radius: `Xpx`
- Border: `[1px solid #XXXXXX or transparent or none]`
- Font: `[size] [family] weight [N], "[opentype feature]"`
- Hover: [description of hover state]
- Active: [description of active/pressed state]
- Focus: `[2px solid #XXXXXX]` outline
- Use: [Describe when to use this variant — e.g. "Primary CTA: 'Get Started', 'Buy'"]

**[Secondary Variant — e.g. Ghost / Outlined]**
- Background: `transparent`
- Text: `#XXXXXX`
- Padding: `Xpx Xpx`
- Radius: `Xpx`
- Border: `1px solid #XXXXXX`
- Hover: [description]
- Use: [Secondary actions]

**[Tertiary / Pill / Badge Variant]**
- Background: `#XXXXXX`
- Text: `#XXXXXX`
- Padding: `Xpx Xpx`
- Radius: `9999px` (full pill)
- Font: `Xpx weight N`
- Use: [Status badges, tags, pills]

### Cards & Containers
- Background: `#XXXXXX`
- Border: `1px solid #XXXXXX` (or via shadow — `rgba(...) 0px 0px 0px 1px`)
- Radius: `Xpx` (standard), `Xpx` (featured)
- Shadow: `rgba(X,X,X,X.XX) 0px Xpx Xpx Xpx[, second layer if multi-layer]`
- Hover: [shadow intensification / transform / none]
- Notes: [Any distinctive treatment — e.g. image cards have top-only radius `12px 12px 0 0`]

### Badges / Tags / Pills
**[Badge Variant — e.g. Success Badge]**
- Background: `rgba(X,X,X,X.X)`
- Text: `#XXXXXX`
- Padding: `Xpx Xpx`
- Radius: `Xpx`
- Border: `1px solid rgba(X,X,X,X.X)`
- Font: `Xpx weight N`

### Inputs & Forms
- Background: `#XXXXXX`
- Border: `1px solid #XXXXXX`
- Radius: `Xpx`
- Focus: `[1px solid accent-color]` or ring outline
- Label: `#XXXXXX`, `Xpx [family]`
- Text: `#XXXXXX`
- Placeholder: `#XXXXXX`

### Navigation
- [Describe: sticky or static, background and blur/glass effect if any]
- Brand logo: [alignment, approximate size]
- Links: `[font family] Xpx weight N`, `#XXXXXX` text
- Active: [underline / color shift / weight change]
- CTA: [color and position — e.g. right-aligned, pill button]
- Mobile: [hamburger / full-screen overlay / drawer]

### [Brand-Specific Distinctive Component 1 — e.g. "Product Hero Module"]
- [Describe structure, key measurements, and visual treatment]

### [Brand-Specific Distinctive Component 2 — e.g. "Workflow Pipeline"]
- [Describe structure, key measurements, and visual treatment]

## 5. Layout Principles

### Spacing System
- Base unit: `8px`
- Scale: `[list key values — e.g. 2px, 4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px]`
- Notable: [One sentence on anything unusual — e.g. dense at small sizes, skips 20px/24px]

### Grid & Container
- Max content width: approximately `[Xpx]`
- Hero: [describe layout — e.g. centered single-column with generous padding]
- Feature sections: [describe — e.g. 2–3 column grids for feature cards]
- [Any full-width section treatment]

### Whitespace Philosophy
- **[Name for the whitespace style]**: [1–2 sentences describing the approach — e.g. "Gallery emptiness", "Cinematic breathing room", "Precision spacing"]
- **[Section rhythm]**: [How sections are separated — e.g. background color alternation, border-only, spacing alone]
- **[Density strategy]**: [How dense vs. open the content areas feel]

### Border Radius Scale
- Micro (`[X]px`): [Fine-grained elements]
- Standard (`[X]px`): [Buttons, inputs, badges — the workhorse]
- Comfortable (`[X]px`): [Standard card containers]
- Large (`[X]px`): [Featured/hero elements]
- Full Pill (`9999px` or `980px`): [Badges, pills, signature CTA links]
- Circle (`50%`): [Avatars, media controls]

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat (Level 0) | No shadow | Page background, text blocks |
| [Level 1 name] | `rgba(X,X,X,X.XX) 0px Xpx Xpx` | [Subtle lift context] |
| [Level 2 name] | `[CSS shadow value]` | [Standard cards, panels] |
| [Level 3 name] | `[CSS shadow value — often multi-layer]` | [Elevated/featured elements, dropdowns] |
| [Level 4 / Modal] | `[CSS shadow value]` | [Modals, floating panels] |
| Focus (Accessibility) | `2px solid #XXXXXX` outline | Keyboard focus on all interactive elements |

**Shadow Philosophy**: [2–3 sentences explaining the distinctive shadow strategy — e.g. why the brand uses blue-tinted shadows, the multi-layer architectural approach, what emotions the shadows evoke.]

### Decorative Depth
- [Any non-shadow depth technique — e.g. backdrop-filter glass, background color contrast, product photography shadows]

## 7. Do's and Don'ts

### Do
- [Specific actionable rule tied to a design token — e.g. "Use weight 300 for all headlines and body text — lightness is the signature"]
- [Typography rule — font-feature-settings, weight, tracking]
- [Color rule — which color is used exclusively for what]
- [Shadow / border rule]
- [Radius rule]
- [A layout or whitespace rule]
- [A dark/light section rule if applicable]
- [One more affirmative rule]

### Don't
- [Opposite of a Do — e.g. "Don't use weight 600–700 for headlines — weight 300 is the brand voice"]
- [Anti-pattern for typography]
- [Anti-pattern for color — e.g. "Don't introduce additional accent colors"]
- [Anti-pattern for shadow/border]
- [Anti-pattern for radius]
- [Anti-pattern for whitespace or layout]
- [Anti-pattern for images or decorative elements]
- [One more prohibition]

## 8. Responsive Behavior

### Breakpoints
| Name | Width | Key Changes |
|------|-------|-------------|
| Mobile | <640px | Single column, reduced heading sizes, stacked cards |
| Tablet | 640–1024px | 2-column grids, moderate padding |
| Desktop | 1024–1280px | Full layout, 3-column feature grids |
| Large Desktop | >1280px | Centered content with generous margins |

### Touch Targets
- [Primary CTA minimum size — e.g. "8px–16px vertical padding creating ~44px touch height"]
- [Navigation link spacing]
- [Badge/pill minimum tap target]
- [Mobile toggle button treatment]

### Collapsing Strategy
- Hero: `[Xpx]` display → `[Xpx]` → `[Xpx]` on mobile, [note what's maintained — e.g. weight, tracking]
- Navigation: [full horizontal layout] → [mobile treatment]
- Feature cards: 3-column → 2-column → single column stacked
- [Any section that requires special treatment on mobile]
- Section spacing: `[Xpx]+` → `[Xpx]` on mobile

### Image Behavior
- [How product/hero images scale]
- [Border/shadow treatment on images across breakpoints]
- [Any images that crop vs. maintain aspect ratio]

## 9. Agent Prompt Guide

### Quick Color Reference
- Primary CTA: [Color Name] (`#XXXXXX`)
- CTA Hover: [Color Name] (`#XXXXXX`)
- Background: [Color Name] (`#XXXXXX`)
- Alt Background *(if applicable)*: [Color Name] (`#XXXXXX`)
- Heading text: [Color Name] (`#XXXXXX`)
- Body text: [Color Name] (`#XXXXXX`)
- Secondary text: [Color Name] (`#XXXXXX`)
- Border: [value]
- Link: [Color Name] (`#XXXXXX`)
- Focus ring: [Color Name] (`#XXXXXX`)
- [Any brand-specific token worth calling out]

### Example Component Prompts
- "[Detailed, copyable prompt for hero section — include exact px, weight, line-height, letter-spacing, color hex, radius, padding values]"
- "[Detailed prompt for a card]"
- "[Detailed prompt for a badge/pill]"
- "[Detailed prompt for navigation]"
- "[Detailed prompt for a section or brand-specific component]"

### Iteration Guide
1. [Most critical rule #1 — the one thing every generated component must follow]
2. [Letter-spacing / tracking formula across sizes]
3. [Weight system reminder]
4. [Shadow / border formula]
5. [Color constraint — e.g. the only saturated color is X]
6. [Dark/light section rule if applicable]
7. [Monospace / code font rule if applicable]
8. [One more critical reminder — often the "inner detail" that's easy to forget]
```

---

## Specification

### File Naming & Location

```
design-md/
└── [brand-slug]/
    ├── DESIGN.md          ← the design system document (this template)
    ├── README.md          ← short description + preview screenshots
    ├── preview.html       ← visual token catalog (light)
    └── preview-dark.html  ← visual token catalog (dark)
```

- **Slug format**: lowercase, hyphens for spaces, `.` kept for domains (e.g. `linear.app`, `mistral.ai`)
- **File name**: always `DESIGN.md` in ALL CAPS

---

### Section Rules

#### Section 1 — Visual Theme & Atmosphere

- **Tone**: Editorial, evocative, but grounded in exact values. Think "art critic + engineer".
- **Length**: 2–4 descriptive paragraphs + the **Key Characteristics** bullet list.
- **Key Characteristics list**: 7–10 bullets. Each bullet must be **concrete and specific** — never vague ("clean design"). Include hex values, px values, and CSS property names where relevant.
- **Required coverage**: background strategy, primary typeface + its most distinctive property, the "signature move", accent color deployment.

#### Section 2 — Color Palette & Roles

- **Format per color**: `**Name** (\`#XXXXXX\`)`: role description.
  - Optionally append the CSS variable: `**Name** (\`#XXXXXX\`): \`--token-name\`. Description.`
  - For rgba values: `**Name** (\`rgba(R,G,B,A)\`)`: role.
- **Sub-groups**: Organize by semantic function. Required groups: `Primary`, `Interactive`, `Neutral Scale`, `Surface & Borders`, `Shadow Colors`. Add brand-specific groups as needed (e.g. `Workflow Accents`, `Status Colors`).
- **Shadow colors**: List shadow rgba values in this section so the Agent Prompt Guide can reference them by name.
- **Completeness**: Aim for 15–30 colors. Every color used in Section 4 (components) must appear here.

#### Section 3 — Typography Rules

- **Font Family sub-section**: List primary + monospace (if used) with their full fallback stacks. Document OpenType features enabled.
- **Hierarchy table**: Minimum 10 rows; maximum ~18. Cover the full scale from display hero down to micro/nano.
  - **Size format**: `Xpx (X.XXrem)` — always include both units.
  - **Line Height format**: ratio + a descriptor in parentheses: `1.07 (tight)`, `1.50`, `1.80 (relaxed)`.
  - **Letter Spacing**: `normal` or `−X.XXpx`. Negative values are common at large sizes.
  - **Weight**: Numeric (e.g. `300`, `400`, `510`, `600`), not named (not "semibold").
- **Principles sub-section**: 3–5 bullets. Each covers a distinctive typographic decision and explains *why* it exists.

#### Section 4 — Component Stylings

- **Buttons**: Document every visual variant (primary, secondary/ghost, tertiary, pill/badge). For each:
  - Background, Text, Padding, Radius, Border, Font spec, Hover state, Active state (if distinct), Focus state, Use case.
- **Cards & Containers**: Document background, border (or shadow-as-border), radius, shadow stack, hover.
- **Navigation**: Always include. Cover: background (including any blur/glass effect), link font spec, CTA position, mobile behavior.
- **Inputs & Forms**: Background, border, radius, focus, label, text, placeholder colors.
- **Badges / Tags / Pills**: Always document at least one badge variant.
- **Brand-specific components**: Add 1–3 sections for the most distinctive UI patterns on the site (e.g. "Workflow Pipeline", "Product Hero Module", "Trust Bar / Logo Grid").

#### Section 5 — Layout Principles

- **Spacing System**: State the base unit (almost always 8px). List the key scale values. Note any unusual gaps or dense regions.
- **Grid & Container**: State max content width. Describe hero, feature section, and full-width section treatments.
- **Whitespace Philosophy**: 2–3 named paragraphs. Each has a **bold heading** (the name of the philosophy) followed by 1–2 sentences.
- **Border Radius Scale**: List every distinct radius used in the system with a role label.

#### Section 6 — Depth & Elevation

- **Table**: Use the Level / Treatment / Use format. 4–6 rows minimum, always ending with the Focus (Accessibility) row.
- **Treatment column**: For levels 1+, always write the full CSS `box-shadow` value, not a description.
- **Shadow Philosophy**: 2–3 sentences. Explain *what's distinctive* about how the brand uses shadows (not just what the values are).
- **Decorative Depth**: Cover non-shadow depth techniques (glassmorphism, background color contrast, photography-driven depth).

#### Section 7 — Do's and Don'ts

- **8 Do's and 8 Don'ts** (minimum 6 each).
- Each rule must be **actionable and specific** — tied to a named token, a px value, or a CSS property.
- Do NOT write vague rules like "Keep it clean" or "Be consistent".
- The Do's and Don'ts together should cover: typography (weight, tracking, OpenType), color (which colors go where), shadow/border, radius, whitespace, and images.

#### Section 8 — Responsive Behavior

- **Breakpoints table**: Minimum 4 breakpoints (Mobile, Tablet, Desktop, Large Desktop). Add intermediate breakpoints if the brand has them.
- **Touch Targets**: Reference WCAG 44×44px minimum. Document actual padding values.
- **Collapsing Strategy**: Cover headline size reduction, navigation collapse, grid collapse, section spacing reduction.
- **Image Behavior**: Cover product image scaling, border/shadow persistence, any crop behavior.

#### Section 9 — Agent Prompt Guide

- **Quick Color Reference**: A short lookup table in key: value format. Cover 8–12 tokens that agents will need most often.
- **Example Component Prompts**: 5 copyable prompts. Each must be self-contained (no reference to "use the colors above") — all values spelled out inline. Cover: hero section, card, badge/pill, navigation, one brand-specific component.
- **Iteration Guide**: 6–8 numbered rules. These are the distilled "never forget" rules for any agent generating UI. Order them by importance — the most critical constraint goes first.

---

### Writing Style Conventions

| Convention | Rule |
|-----------|------|
| **Color references** | Always include the hex/rgba in backtick code spans: `` `#533afd` `` |
| **CSS values** | Always in code spans: `` `rgba(50,50,93,0.25) 0px 30px 45px -30px` `` |
| **Font name in prose** | Use backticks for font-family strings: `` `sohne-var` ``, `` `Inter Variable` `` |
| **CSS variable names** | Inline code span: `` `--hds-color-heading-solid` `` |
| **OpenType features** | Use the quoted CSS syntax: `"ss01"`, `"liga"`, `"tnum"` |
| **Weight values** | Numeric always: `300`, `510`, `600` — never "semibold" or "bold" alone |
| **Size notation** | Dual: `48px (3.00rem)` |
| **Line height notation** | Ratio + descriptor: `1.07 (tight)`, `1.50`, `1.80 (relaxed)` |
| **Section headings** | `## N. Section Title` — always numbered, always title-case |
| **Component variant headings** | `**Bold Name**` without `###` — e.g. `**Primary Blue**`, `**Ghost / Outlined**` |
| **Bullet style** | Unordered (`-`) for all lists inside sections |
| **Table alignment** | Left-align all columns (default) |
| **Document title** | `# Design System Inspiration of [Brand Name]` |
| **Tone** | Precise and evocative. Explain *why* a choice exists, not just *what* it is |

---

### Quality Checklist

Before submitting a `DESIGN.md`, verify:

- [ ] All 9 sections are present and in order
- [ ] Section 1 has at least 7 Key Characteristics bullets with hex/px values
- [ ] Section 2 has organized sub-groups; every shadow rgba is named here
- [ ] Section 3 typography table has ≥10 rows; all sizes in `Xpx (X.XXrem)` format
- [ ] Section 4 documents ≥2 button variants, cards, navigation, inputs, and ≥1 badge
- [ ] Section 5 includes base unit, key spacing scale, and Whitespace Philosophy with named paragraphs
- [ ] Section 6 elevation table has ≥4 levels; Shadow Philosophy paragraph is present
- [ ] Section 7 has ≥6 Do's and ≥6 Don'ts; every rule is specific and actionable
- [ ] Section 8 has ≥4 breakpoints; Collapsing Strategy and Image Behavior are present
- [ ] Section 9 Example Component Prompts are fully self-contained (all values inline)
- [ ] No vague language ("clean", "minimal", "modern") without supporting specifics
- [ ] All hex values are valid; rgba values sum to ≤1.0 for the alpha channel
- [ ] Document title matches the brand name in the directory slug
