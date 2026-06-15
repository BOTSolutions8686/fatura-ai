# Fatura AI — Task Backlog
<!-- Orchestrated by Cowork. Last updated: 2026-06-15 05:45 -->
<!-- Format: [ID] Title | Agent | Priority | Status | Dependencies -->

## 🔴 In Progress
- [T015] Write unit tests for item matching | aider | P1 | DONE | T006

## 📋 Backlog

### P1 — Important for release
- [T013] Write Arabic translations for all __()/() strings | opencode | P1 | TODO | T007
- [T016] Write unit tests for AI extraction | aider | P1 | TODO | T003,T004
- [T018] Code review pass — review all Aider/OpenCode output | claude-code | P1 | TODO | T012

### P2 — Nice to have
- [T020] Performance: batch item matching caching | aider | P2 | TODO | T006

## ✅ Done
- [T001] Scaffold Frappe app structure + DocTypes | claude-code | P0 | DONE | none
- [T002] Implement FaturaSettings DocType logic (validation, API key storage) | aider | P0 | DONE | T001
- [T003] Implement AI extraction module — Anthropic provider (fatura_ai/ai_extraction.py) | aider | P0 | DONE | T001
- [T004] Implement AI extraction module — OpenAI provider | opencode | P0 | DONE | T001
- [T005] Implement 3-tier supplier matching logic (fatura_ai/supplier_matching.py) | aider | P0 | DONE | T001
- [T006] Implement 3-tier item matching logic (fatura_ai/helpers/item_matching.py) | opencode | P0 | DONE | T001
- [T007] Build 5-step wizard — Step 1: File Upload UI (JS + Python endpoint) | aider | P0 | DONE | T001
- [T008] Build 5-step wizard — Step 2: AI Extraction preview UI | opencode | P0 | DONE | T007
- [T009] Build 5-step wizard — Step 3: Supplier matching review UI | aider | P0 | DONE | T005,T008
- [T010] Build 5-step wizard — Step 4: Item matching review UI | opencode | P0 | DONE | T006,T008
- [T011] Build 5-step wizard — Step 5: Confirm + create PI/PO (never auto-submit) | aider | P0 | DONE | T009,T010
- [T012] ksa_compliance integration — link Fatura import to ZATCA fields | claude-code | P0 | DONE | T011
- [T014] Write unit tests for supplier matching | aider | P1 | DONE | T005
- [T017] FaturaImportLog — implement status tracking and error logging | aider | P1 | DONE | T001
- [T019] Google Gemini AI provider | opencode | P2 | DONE | T003

## 🚫 Blocked
<!-- Tasks waiting on external dependency -->
