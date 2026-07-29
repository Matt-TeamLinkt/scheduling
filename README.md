# TeamLinkt Design System

A design system distilled from TeamLinkt's brand assets, product Figma files, and live product surfaces. Intended to be used by design agents (and humans) to create on-brand interfaces, marketing pages, slide decks and prototypes.

## What is TeamLinkt?

TeamLinkt is an all-in-one **sports management platform** for leagues, clubs, associations, parks & rec departments, governing bodies, and tournament organizers. It consolidates registration, payments, scheduling, scorekeeping, website-building, communications, fundraising and reporting into a single connected platform — replacing a stack of single-purpose tools. It is **trusted by 3,500+ sports organizations** across hockey, soccer, baseball, basketball, football, volleyball, lacrosse, cheerleading, e-sports and more.

Two halves of the product:

1. **The admin platform** (web) — `app.teamlinkt.com`, `leagues.teamlinkt.com`. League/club administrators use this to build registration forms, generate schedules, manage rosters, run tournaments, build the public website, run fundraisers, and pull reports.
2. **The Team App** (iOS / Android, also mobile-web) — used by coaches, parents and players. Schedules, rosters, RSVPs, group + DM chat, photo sharing, live scoring, push reminders, payments.

A third pillar: **Emi**, an AI assistant embedded in the admin platform that drafts schedules, registration forms, and announcements from natural language.

## Sources used to build this system

- `uploads/teamlinkt.webp` — full TeamLinkt wordmark (blue check + "TeamLinkt").
- `uploads/unnamed.webp` — square TeamLinkt mark only.
- Figma file: **Attach rate – Q2 2026** — onboarding "Delight" / mobile screen, header pattern, marketing-style imagery. Origin of Be Vietnam Pro type, brand blue `rgb(36,84,255)` and the light-blue tint panel.
- Figma file: **HCR integrations** — admin form-level surfaces, internal vs. org-view headers, button variants (Solid / Soft / Ghost), age-group widgets.
- Figma file: **Background checks (JDP)** — research/discovery + V0.5 + V1 release flows for player background checks.
- Figma file: **Radix Unstyled (Community)** — generic Radix primitives library, used only as a reference for *component anatomy* (accordion, dialog, popover, etc.). It is **not** the visual brand; TeamLinkt's actual styling overrides everything.
- Web sources: teamlinkt.com (homepage, sports-management-software, team-app, tournaments, governing-bodies, all-in-one), help.teamlinkt.com.

> Reader: you may not have access to the original Figma files. The values, examples, and patterns recorded in this folder are the canonical source of truth.

---

## CONTENT FUNDAMENTALS

**Voice.** Warm, plain-spoken, second-person. TeamLinkt talks *to* the administrator, parent, or coach as a peer. Sentences are short. Verbs are active.

- **You-form**, almost never "we" except in support/testimonial copy. ("Make it easy for players and teams to join your multi-sport clubs…")
- **Sentence case** for headings, buttons and nav. ("Your account's all set – Let's get started!", "Start now", "Audit history", "Publish")
- **Em dashes and exclamation marks** are common in onboarding flows — they're the warmest part of the voice. ("We're excited you're here! — To kick things off, let's set up registration and payments…")
- **Numbers do the talking.** Concrete time/savings numbers are used heavily on marketing surfaces: "3,500+ programs globally", "save 15 hours per week", "63 hours saved on admin work", "10 hours per week immediate savings".
- **Verbs of consolidation:** "all-in-one", "in one place", "one connected platform", "single, connected system". Never "suite" or "ecosystem".
- **Sports-neutral by default** — copy applies across hockey, soccer, etc. When it gets specific, it lists representative sports rather than picking one ("hockey, soccer, baseball, basketball, football, lacrosse, volleyball").
- **No emoji** in the product UI. None observed in marketing pages either. Don't add them.
- **No corporate jargon** ("synergize", "leverage", "ecosystem"). Plain words: "manage", "run", "build", "share", "track", "keep connected".
- **Tone for errors** — direct and helpful, not clever. Help-center copy is task-titled: "Find a Team's Join Code", "Why can't I issue a refund?", "Display Practices on Website".
- **Calls to action** are imperative + concrete: "Start now", "Get a Demo", "Create Free Account", "Try now", "Publish", "Share form", "Audit history".

**Examples (verbatim from product/site):**
- Headline: "Your account's all set - Let's get started!"
- Sub: "We're excited you're here! — To kick things off, let's set up registration and payments for your season participants."
- Section header: "An all-in-one sports management platform"
- Button: "Start now"
- Button: "Publish"
- Footer: "Copyright © 2024 TeamLinkt Inc. · All rights reserved."

---

## VISUAL FOUNDATIONS

### Color
- **Primary brand:** TeamLinkt Blue `rgb(36,84,255)` — used on the logo check, primary CTAs (pill-shaped), and key fills. Pressed/accent variant is `rgb(0,90,255)`.
- **Brand-tinted surfaces:** the very-light blue panel `rgb(235,242,255)` is the brand's signature background — used as a full-bleed welcome-screen halo or "TeamLinkt zone" panel, often with a giant white logo mark layered on it.
- **Soft blue button bg:** `rgba(1,68,255,0.06)` — used for secondary "soft" buttons.
- **Neutrals are warm-cool grays.** True black (`rgb(0,0,0)`) for headlines; `rgb(32,32,32)` for body; `rgb(112,112,123)` for muted labels and icon defaults; `rgb(249,249,249)` and `rgb(250,250,250)` are the two background grays used for top-bar/section fills.
- **Dark UI:** `rgb(28,32,36)` is the near-black used for high-contrast solid buttons (e.g. "Publish"). A darker `rgb(68,68,68)` shows up as the design-canvas / preview-section background.
- **Semantic:** `rgb(243,0,13)` red, `rgb(48,164,108)` green, `rgb(229,159,41)` warning amber.

### Type
- **Be Vietnam Pro Variable** for everything. Weights observed: Regular (400), Medium (500), occasionally Semibold (600).
- **Letter-spacing** is consistently `-0.020em` across every text block. This is a deliberate stylistic choice — keep it.
- **Tight line-heights**: 16/20/28 for the common 12/14/16/24 sizes.
- **Display sizes** appear in marketing only — 40 / 80 / 200 px for hero numerics ("3,500+").
- **Material Symbols Rounded** is used for icons; never mixed with another icon font in the same surface.

### Iconography
See `ICONOGRAPHY.md`. TL;DR: **Material Symbols Rounded** at 20px, weight 400, fill 0 by default; muted gray `rgb(112,112,123)`.

### Imagery
- **Photography** is warm, action-oriented sport candids. Cropped tight on faces or hands-on-equipment. Skin tones rendered naturally; no heavy color grading.
- **Brand graphic** = the **TeamLinkt check mark** (square white-on-blue or white-on-tint). Used scaled to ~80–120% of the panel height as a watermark/halo behind copy. Never tilted, never cropped at random — it's always the full mark, anchored to a corner.
- **No hand-drawn illustrations.** No isometric scenes. No 3D renders. No abstract gradients.
- **No emoji-as-decoration.** No sticker packs.

### Backgrounds
- Mostly **flat white** (`#fff`) or the off-white `rgb(249,249,249)`.
- The **light-blue tint panel** (`rgb(235,242,255)`) is the one moment of color — used as a full-bleed welcome surface, with the white check-mark watermark at huge scale.
- No noise, no grain, no gradients on production UI. (Subtle inner-shadow `rgba(14,18,22,.07)` on cards; that's the only "depth".)

### Layout & spacing
- **4-pixel spacing grid.** Standard spacings: 4, 8, 12, 16, 24, 32, 48, 64.
- **Top bars** are a 64px outer / 48px inner pattern — the inner "pill" is wrapped in 8px padding from the viewport, has 12px radius, and sits on `rgb(250,250,250)`.
- **Page heads** sit on `rgb(249,249,249)` with 24px padding, 16px gap between back-arrow / title / right-aligned action cluster.
- **Cards** use 12px radius and the divider hairline `rgb(225,227,234)`.
- Layouts feel **roomy and content-first** — generous whitespace, low information density, very little decorative chrome.

### Corner radii
- 8 (small chips), **10 (icon-button wells, secondary buttons)**, **12 (top-bar pill, cards, inputs)**, 16, **100 (pill primary CTA)**.

### Borders, dividers, shadows
- Hairline divider: `1px solid rgb(225,227,234)`.
- Visible border (input, tag): `1px solid rgb(209,209,214)`.
- Shadows are *very* light — `0 1px 2px rgba(14,18,22,.07)` is the workhorse. Anything heavier is reserved for floating menus / popovers.

### Hover & press states
- **Primary pill button** — hover darkens to `rgb(0,90,255)`; press translates 1px down. No shadow change.
- **Soft / ghost buttons** — hover bumps the soft tint by ~50% (e.g. `rgba(1,68,255,0.10)` from `0.06`).
- **Icon buttons** — hover fills with `rgba(1,68,255,0.06)`.
- **Links / nav items** — slight color shift toward the brand blue.
- **No bouncy springs**, no scale-up animations on hover.

### Animation
- **Fades and 150–200ms ease-out** for state changes.
- **No bounces, no parallax, no Lottie illustrations** in product UI.
- Page transitions: instant or a 200ms cross-fade.

### Transparency / blur
- **No glass / no backdrop-filter** in observed surfaces. Solid colors, period.

### Cards
- White fill, 12px radius, `1px solid rgb(225,227,234)` border, optional shadow `0 1px 2px rgba(14,18,22,.07)`. Never colored-left-border accents.

### Layout rules (fixed elements)
- Top app bar: fixed 64px height across all logged-in surfaces.
- Footer (marketing pages): horizontal links + copyright on `rgb(250,250,250)`, 48px inner row.
- Forms: max-width 720–840px, single column, generous 24–32px between blocks.

---

## Folder index

```
README.md                    ← you are here
SKILL.md                     ← agent skill manifest
ICONOGRAPHY.md               ← icon system & usage rules

colors_and_type.css          ← CSS variables (brand + semantic)
fonts/                       ← (Be Vietnam Pro is loaded via Google Fonts in the CSS)

assets/                      ← logos, mark, brand images
  teamlinkt-logo.webp        ← full wordmark (blue)
  teamlinkt-mark.webp        ← square mark (blue, white check)
  teamlinkt-wordmark-blue.svg
  teamlinkt-icon-white.svg

preview/                     ← design-system preview cards (Design System tab)

ui_kits/
  admin/                     ← admin platform UI kit (web)
  team-app/                  ← Team App UI kit (mobile)

SKILL.md                     ← agent-skill manifest (use this in Claude Code)
```

---

## Caveats / known gaps

- **Be Vietnam Pro Variable** is loaded via Google Fonts (the variable axis collapses to instance weights 300/400/500/600/700). If a designer needs the true variable file, please drop the `.ttf` into `fonts/` and update `colors_and_type.css`.
- The Figma files I had access to are *internal product* Figmas (Attach rate, HCR integrations, Background checks). They do **not** include the public marketing site components or the full Team App screen library. The UI kits below are reasoned from these surfaces + public screenshots + help-center copy — they are high-fidelity but not pixel-comprehensive.
- The "Radix Unstyled" Figma file was treated as a *component-anatomy* reference only.
