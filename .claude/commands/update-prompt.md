# /update-prompt
# Triggers the prompt improvement cycle. Always runs tests before and after.

When this command is invoked:

1. Run /test-invoice first to get current baseline scores.
   Save baseline to tests/results/pre_prompt_update.json.

2. Invoke prompt-engineer subagent.
   Pass it:
   - Current prompt location: fatura_ai/templates/prompts/extraction_prompt.txt
   - Baseline scores from step 1
   - docs/PROMPT_LOG.md for history

3. After prompt-engineer writes the updated prompt:
   Run /test-invoice again with the new prompt.
   Save new results to tests/results/post_prompt_update.json.

4. Compare before vs after:

   PROMPT UPDATE RESULTS
   ━━━━━━━━━━━━━━━━━━━━━
   Before: XX% overall
   After:  XX% overall
   Delta:  +X% / -X%

   Category breakdown:
   [show per-category before/after]

5. If improved (overall delta positive):
   - Commit the new prompt: git add + git commit -m "prompt/vX.Y description"
   - Update docs/PROMPT_LOG.md automatically

6. If worse (overall delta negative):
   - Revert: git checkout fatura_ai/templates/prompts/extraction_prompt.txt
   - Report: "Prompt change made scores worse. Reverted. See PROMPT_LOG.md for notes."
   - Document the failed attempt in PROMPT_LOG.md anyway

7. Never change code during a /update-prompt session.
