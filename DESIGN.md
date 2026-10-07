---
name: Oversight desk
description: A parliamentary order paper, one white sheet on minute-book cloth.
colors:
  order-paper-red: "#9e2a2b"
  minute-book-green: "#1c3a2e"
  paper: "#ffffff"
  ink: "#1a1612"
  cloth-cream: "#f4efe6"
  ledger-green: "#1e3d32"
typography:
  display:
    fontFamily: "Source Serif 4, serif"
    fontSize: "2.4rem"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Source Serif 4, serif"
    fontSize: "1.4rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Source Serif 4, serif"
    fontSize: "1.15rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.015em"
  body:
    fontFamily: "Source Serif 4, serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Source Serif 4, serif"
    fontSize: "1.0625rem"
    fontWeight: 600
    lineHeight: 1.5
rounded:
  none: "0"
spacing:
  form-gap: "0.5rem"
  control: "0.7rem"
  field: "0.85rem"
  stack: "1.15rem"
  cloth-x: "1.25rem"
  stage: "1.45rem"
  cloth-bottom: "4rem"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0.7rem 1.1rem"
  button-primary-hover:
    backgroundColor: "{colors.order-paper-red}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0.7rem 1.1rem"
  question-field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "0.75rem 0.85rem"
    width: "100%"
  question-label:
    textColor: "{colors.ink}"
    typography: "{typography.label}"
  outcome-plate:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "1.05rem 1.15rem"
  turn-control:
    backgroundColor: "{colors.minute-book-green}"
    textColor: "{colors.cloth-cream}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "0.55rem 0"
  stage-list:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.title}"
    rounded: "{rounded.none}"
    padding: "0"
  sheet:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "2.4rem 2.3rem 2.6rem"
  sheet-link:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
---

# Design System: Oversight desk

## Overview

**Creative North Star: "The Parliamentary Order Paper"**

The Parliamentary Order Paper is one white sheet on a minute-book green cloth. A single serif, one red rule, and square cuts do the work. The sheet is where the reading sits. The cloth is the table under it. Density follows a printed paper: a title, a rule, prose, a field, and a flat plate. Equal cards, status lamps, and a monospace costume are not part of this system.

Source Serif 4 is self-hosted and falls back to serif. Weight 600 carries the title, the headings, the label, and the button. Weight 400 is the reading text. Italic 400 is the turn control and the asides. Corners stay at zero. The sheet casts the only shadow. The outcome is a plate with a 1px ink border and no shadow. The sheet turns to its other face, and reduced motion swaps the faces with no animation.

Regions separate by a line, not by a tint. Ink reads on paper, cream reads on the cloth, and ledger green is only the italic aside. A stage that did not run is struck through in ink. Red is the rule, the caret, the underline, the focus ring on the sheet, or the hover.

**Key Characteristics:**

- White paper on minute-book green cloth
- One red accent, used as a rule rather than a resting fill
- Source Serif 4 only, self-hosted
- Square corners (0)
- One soft shadow, under the sheet
- Idle stages struck through in ink, not recolored

## Colors

Green cloth, white paper, warm ink, and one red rule.

### Primary

- **Order-paper red** (#9e2a2b): The 1px rule under the title. Also the selection fill, the caret, error text, link underlines, stage numerals, the button's hover fill, and the focus ring on the sheet (2px, offset 3px). Selected text on that fill is paper.

### Neutral

- **Minute-book green** (#1c3a2e): The cloth. The page ground, the sticky bar behind the turn control, and the scrollbar track.
- **Paper** (#ffffff): The sheet, the field, the plate, button lettering, and selected text.
- **Ink** (#1a1612): Headings and body on the sheet, the field border, the plate border, link text at rest, the button's resting fill, and the strike through an idle stage.
- **Cloth cream** (#f4efe6): Lettering on the cloth, the running line, the scrollbar thumb, and the turn control's focus ring (2px, offset 4px).
- **Ledger green** (#1e3d32): Italic asides on the sheet, including the book line and the note when nothing has run.

### Named Rules

**The One Accent Rule.** Order-paper red is a line, a caret, an underline, a focus ring on the sheet, or a hover. It is not a second background, and it is not a status lamp.

**The Ground Rule.** Cream is the text on the cloth. Ink is the text on the sheet. Ledger green is only the italic aside.

## Typography

**Display Font:** Source Serif 4 (with serif)
**Body Font:** Source Serif 4 (with serif)

**Character:** One text face, self-hosted, does every role. The shipped files are roman 400, roman 600, and italic 400. Synthesis is off, so a bold italic is not available. Titles and headings balance their lines.

### Hierarchy

- **Display** (600, 2.4rem, line-height 1.05, tracking -0.02em): The sheet title. Below 640px it is 2rem.
- **Headline** (600, 1.4rem, line-height 1.25, tracking -0.02em): The question and the section headings. A heading that follows the rule sits 0.15rem under it; other headings take 1.8rem above and 0.45rem below. Below 640px the size is 1.25rem.
- **Title** (600, 1.15rem, line-height 1.3, tracking -0.015em): A stage name. The numeral in front of it is order-paper red.
- **Body** (400, 1.0625rem, line-height 1.5): Reading text on the sheet. The column is 40rem wide.
- **Label** (600, 1.0625rem, line-height 1.5): The question label and the button. Same size as body; weight marks them. Not uppercase.

Italic 400 is the turn control, the running line, and the ledger-green asides. It is not used for headings.

### Named Rules

**The One Face Rule.** Source Serif 4 sets every role. Do not add a sans, and do not add a monospace face.

**The Loaded Weights Rule.** The files are roman 400, roman 600, and italic 400, and the page turns synthesis off. Do not call for a bold italic.

## Layout

The cloth fills the viewport and pads it 1.6rem on top, 1.25rem at the sides, and 4rem at the bottom. The scene is one centered column at the narrower of 40rem and the viewport. The turn control sticks to the top of that column, aligned to the end, on a cloth-colored bar (0.55rem of vertical padding, 0.85rem beneath) so the sheet can pass under it. The two faces of the sheet share one cell. The face is padded 2.4rem 2.3rem 2.6rem. Long words break anywhere, so a question cannot widen the sheet.

Below 640px the cloth padding becomes 1rem 0.85rem 2.5rem, the face padding becomes 1.45rem 1.15rem 1.7rem, and the button stretches to the column.

The rhythm is rem, not a 4px grid. The form stacks on a 0.5rem gap. Control padding is 0.7rem on the vertical. The field's side inset and the gap above the sheet are 0.85rem. The form and the plate open with 1.15rem. The rule's margin and the cloth's side padding are 1.25rem. Stages sit 1.45rem apart. The cloth keeps 4rem below the column.

### Named Rules

**The Column Rule.** The scene is one centered column at the narrower of 40rem and the viewport. Below 640px the column stays full width and the button stretches to it.

## Elevation & Depth

Depth is the sheet on the cloth, not a stack of cards. The sheet is the only lifted surface. Its shadow is soft, offset down and to the right, in a near-black green at 38% opacity, so the paper sits on the table rather than glowing. The plate, the field, and the button are flat. Turning the sheet is the other depth: perspective of 1800px, a half-turn on the Y axis, the reverse face the same paper. Reduced motion drops the transition and shows one face at a time.

### Shadow Vocabulary

- **Sheet** (`box-shadow: 0.55rem 0.85rem 1.7rem rgba(6, 16, 12, 0.38)`): Always, under the sheet. Not on hover. Not on the plate, the field, or the button.

### Named Rules

**The One Shadow Rule.** The sheet carries the shadow 0.55rem 0.85rem 1.7rem rgba(6, 16, 12, 0.38). The plate, the field, and the button stay flat. A region on the paper separates with a 1px ink border, not a second shadow.

**The Still Turn Rule.** The sheet turns on the Y axis in 700ms with cubic-bezier(0.16, 1, 0.3, 1), seen from 1800px of perspective. Reduced motion removes the transition and shows one face at a time.

## Shapes

The cut is square. The button and the field declare a radius of 0. The sheet and the plate declare none, and they are square as well. The field and the plate are closed by a 1px ink border. The red rule is a 1px bar, not a rounded ornament. Underlines are 1px, offset 0.18em on a link and 0.2em on the turn control. An idle stage is struck with a 1.5px ink line.

### Named Rules

**The Square Cut Rule.** Radius is 0 on the button, the field, the plate, and the sheet. Do not round them.

## Components

### Buttons

A square block of ink. The label is the sheet's serif at weight 600. There is no border and no shadow.

- **Shape:** Square corners (0).
- **Primary:** Ink fill, paper text, padding 0.7rem 1.1rem. It sits 0.35rem below the field. Below 640px it stretches to the column.
- **Hover / Focus:** Hover replaces the ink with order-paper red in a straight cut, with no transition. Focus is the sheet ring: 2px order-paper red, offset 3px.
- No secondary, ghost, or tertiary button.

### Cards / Containers

The sheet is the container: paper, square, padding 2.4rem 2.3rem 2.6rem (1.45rem 1.15rem 1.7rem below 640px), and the one shadow. It is not a card. The outcome plate is a ruled block on that same paper: a 1px ink border, padding 1.05rem 1.15rem, square, and no shadow. Outcome text keeps its line breaks.

### Inputs / Fields

The question field is square, paper inside a 1px ink stroke, padding 0.75rem 0.85rem, at least 7.5rem tall, and it resizes vertically. The caret is order-paper red. Focus uses the sheet ring, 2px order-paper red, offset 3px. The label is body size at weight 600. An error is order-paper red at weight 600, set above the field. No disabled style is defined.

### Navigation

The turn control is an italic cream underline on the cloth, aligned to the end of the column, not a button. Hover turns it paper white. Its focus ring is cloth cream, 2px, offset 4px. While the desk is working, an italic cream line sits centered on the cloth above the column. Links on the sheet are ink with a 1px order-paper red underline, offset 0.18em. Hover turns the words order-paper red. There is no tab bar.

### Stage list

Names are title type. A numeral in order-paper red stands in front of each name, taken from the list order, because that sequence is the audit. It is not a label set above the heading, and other sections do not grow numerals of their own. A stage that ran is ordinary ink. A stage that did not run keeps its ink and is struck through at 1.5px. The line under the name is body text and keeps its line breaks.

### Named Rules

**The Strike Rule.** A stage that did not run is struck through in ink at 1.5px. Its color does not change.

### Red rule

One 1px order-paper red bar under the title, with 1.25rem beneath it. One on a face that has a title.

## Do's and Don'ts

### Do:

- **Do** set reading text in ink on paper, and cloth text in cream on minute-book green.
- **Do** use self-hosted Source Serif 4 at roman 400, roman 600, or italic 400, with a serif fallback.
- **Do** keep the radius at 0, and separate a region on the paper with a 1px ink border.
- **Do** use the sheet shadow 0.55rem 0.85rem 1.7rem rgba(6, 16, 12, 0.38), and no other shadow.
- **Do** strike an idle stage in ink, and keep order-paper red to the rule, the caret, the underline, the sheet's focus ring, and the hover.

### Don't:

- **Don't** round the button, the field, the plate, or the sheet.
- **Don't** add a second typeface, a monospace face, or a weight the font files do not contain.
- **Don't** shadow the plate, the field, or the button.
- **Don't** use order-paper red as a resting fill, or as a status lamp beside green or amber.
- **Don't** put cream on the sheet or ink on the cloth. The turn control's focus ring stays cream, because red on the cloth does not read.
