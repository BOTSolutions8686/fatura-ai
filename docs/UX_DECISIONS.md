# UX Decision Log
# Document every significant UX decision and the reason behind it.
# This prevents revisiting the same debates and gives Claude Code agents context.

---

## D01 — Button placement: top of form, not actions menu
Decision: "Import Invoice" button appears at the top of the Purchase Invoice form.
Reason: Accountants should see it immediately without hunting through menus.
         Actions menu is for secondary operations. Import is the primary value.
Tradeoff: Adds visual clutter to the form for users who never use it.
Mitigation: Button hidden when document is not in Draft state.

---

## D02 — Never auto-submit
Decision: Fatura AI only populates fields. The user must save and submit manually.
Reason: Accounting users do not trust systems that act without their approval.
         A wrongly submitted invoice creates ZATCA and accounting issues.
         Trust is more important than convenience here.
Tradeoff: One extra click for the user.
No mitigation needed — this is correct behavior.

---

## D03 — Traffic light confidence system (green/amber/red)
Decision: Every matched field shows a confidence indicator, not just a score.
Reason: Accountants understand green/amber/red instantly. A number like 0.72
         means nothing to them. Color communicates action needed.
Tradeoff: Less precise than showing the actual score.
Mitigation: F15 (v1.1) will add numeric score as a secondary detail for power users.

---

## D04 — RTL is field-level, not page-level
Decision: Arabic content within wizard cells is RTL. The wizard itself is LTR.
Reason: ERPNext desk is LTR. Switching the entire wizard to RTL breaks
         Frappe's own button and navigation layout. Field-level RTL is safer.
Tradeoff: Mixed-direction layout requires careful CSS scoping.
Implementation: rtl_handler.js detects Arabic content per field, applies dir="rtl".

---

## D05 — Non-destructive test import in setup
Decision: Setup Step 3 runs a test extraction without creating any doctype.
Reason: Admin should be able to verify the app works without creating test
         documents that need to be cleaned up. Clean setup experience.
Tradeoff: Requires a separate code path for test mode vs real import.
Implementation: API endpoint accepts a test_mode flag, skips doctype creation.

---

## D06 — First-use tips are per-user, not per-site
Decision: Tips shown once per user, not once per site.
Reason: Different accountants start using the app at different times.
         A site-level flag means the second accountant never sees the tips.
Implementation: User-level flag stored in frappe session or User doctype custom field.

---

## D07 — Wizard uses Frappe native Dialog, not custom modal
Decision: wizard_manager.js uses frappe.ui.Dialog as the container.
Reason: Stays consistent with ERPNext UX. Inherits Frappe's keyboard handling,
         accessibility, and theming automatically.
Tradeoff: Limited to what Frappe Dialog supports in terms of layout.
Mitigation: Each step content is injected as HTML into the dialog body,
            giving full layout control within the Frappe container.
