# Next Task for Aider

**Date:** 2026-06-15

## PRIORITY: Stop current work and commit everything done so far.

Run this to see what's staged:
```bash
git add fatura_ai/ api/ && git status
```

Then commit in logical chunks:

**Commit 1 — FaturaImportLog DocType:**
```bash
git add fatura_ai/doctype/fatura_import_log/
git commit -m "feat(T017): implement FaturaImportLog status tracking"
```

**Commit 2 — Settings + extractor changes:**
```bash
git add fatura_ai/fatura_ai/doctype/fatura_ai_settings/fatura_ai_settings.py fatura_ai/api/extractor.py
git commit -m "feat(T008-T011): implement wizard API endpoints"
```

**Commit 3 — New api/ provider module (if intentional):**
```bash
git add api/
git commit -m "feat: add ai provider abstraction layer"
```

**Then push:**
```bash
git push origin develop
```

**Then update TASKS.md:** mark T017, T008, T009, T010, T011 as Done.

**Then STOP and wait** — do not start new tasks until I assign the next one.
