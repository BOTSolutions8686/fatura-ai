# /new-feature
# Scaffolds a new feature with spec, code, and tests in one structured flow.

When this command is invoked:

1. Ask the user:
   - "Which feature ID are you building? (e.g. F03)"
   - "One sentence: what does this feature do?"
   - "Which files will it touch?"

2. Generate a mini-spec showing:
   - Inputs
   - Outputs
   - Edge cases to handle
   - Which existing files it reads from / writes to

3. Show the spec to the user. Wait for explicit approval before writing any code.
   Do not proceed if user says "looks good" vaguely — ask "Should I start coding now?"

4. Invoke frappe-developer subagent to implement.
   Pass it the approved spec and the feature ID.

5. After implementation, invoke qa-reviewer subagent on all changed files.

6. Report to user:
   - Files created/modified
   - Tests written
   - Test results (pass/fail)
   - QA reviewer result (PASS or list of issues)

7. If QA fails: fix issues, re-run QA, report again before closing.
