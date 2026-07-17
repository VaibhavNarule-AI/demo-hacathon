---
name: presentation-standards
description: How to structure the live demo and stakeholder pitch so the audience follows the story, not just the screen. Load when filling 04_DEMO_SCRIPT_TEMPLATE.md or 05_JURY_PITCH_TEMPLATE.md.
---

# Presentation Standards

## Structure
1. **The problem in one sentence** — who hurts, and why today's alternative is bad.
2. **The flow, not the features** — walk one persona through login → action →
   result. Resist the urge to tour every screen.
3. **Show, don't tell, the hard part** — if RBAC is the interesting bit, show a 403
   happen live, not a slide about it.
4. **Proof over promises** — pull up `/health`, `/flow`, and `test_report.html`
   instead of claiming "it's tested."
5. **Land on impact** — close on why this matters beyond the hackathon, in one
   sentence.

## Rules of thumb
- One persona, one flow, one story. Multiple personas dilute the pitch.
- If a diagram from `02_SOLUTION_ARCHITECTURE_TEMPLATE.md` explains the point faster
  than words, show the diagram.
- Rehearse the failure path too (what happens when a wrong role tries to access
  something) — it's often the most convincing part of the demo.
