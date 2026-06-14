# /test-invoice
# Runs the full extraction test suite and reports results.

When this command is invoked:

1. Run: python tests/run_eval.py --all
2. Parse results from tests/results/latest_eval.json
3. Report scores in this format:

   EXTRACTION ACCURACY REPORT
   ━━━━━━━━━━━━━━━━━━━━━━━━━━
   Arabic-only invoices:    XX% (X/X pass)
   English-only invoices:   XX% (X/X pass)
   Mixed invoices:          XX% (X/X pass)
   Scanned/photo invoices:  XX% (X/X pass)
   ─────────────────────────────
   OVERALL:                 XX%
   TARGET:                  85%
   STATUS: PASS / FAIL

   FIELD-LEVEL BREAKDOWN:
   Supplier name:    XX%
   VAT number:       XX%
   Invoice number:   XX%
   Invoice date:     XX%
   Line items:       XX%
   Totals:           XX%

4. Compare to previous run (tests/results/previous_eval.json if exists):
   Show delta per category (+ or - vs last run)

5. If any category is below 85%:
   "⚠️ [Category] is below target. Run /update-prompt to improve."

6. If overall is above 85%:
   "✅ All categories passing target."
