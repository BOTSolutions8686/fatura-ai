# Fatura AI — Task Backlog
<!-- Orchestrated by Cowork. Last updated: 2026-06-15 19:14 -->
<!-- Format: [ID] Title | Agent | Priority | Status | Dependencies -->

## 🔴 In Progress
<!-- none -->

## 📋 Backlog
<!-- none — sprint complete, awaiting new tasks from Talha -->

## 🚫 Blocked

## ✅ Done
- [T001] Scaffold Frappe app structure + DocTypes | claude-code | P0 | DONE | none
- [T002] Implement FaturaSettings DocType logic | aider | P0 | DONE | T001
- [T003] Implement AI extraction — Anthropic provider | aider | P0 | DONE | T001
- [T004] Implement AI extraction — OpenAI provider | opencode | P0 | DONE | T001
- [T005] Implement 3-tier supplier matching logic | aider | P0 | DONE | T001
- [T006] Implement 3-tier item matching logic | opencode | P0 | DONE | T001
- [T007] Build wizard — Step 1: File Upload UI | aider | P0 | DONE | T001
- [T008] Build wizard — Step 2: AI Extraction preview UI | opencode | P0 | DONE | T007
- [T009] Build wizard — Step 3: Supplier matching review UI | aider | P0 | DONE | T005,T008
- [T010] Build wizard — Step 4: Item matching review UI | opencode | P0 | DONE | T006,T008
- [T011] Build wizard — Step 5: Confirm + create PI/PO | aider | P0 | DONE | T009,T010
- [T012] ksa_compliance integration — ZATCA fields | claude-code | P0 | DONE | T011
- [T013] Write Arabic translations for all strings | orchestrator | P1 | DONE | T007
- [T014] Unit tests for supplier matching | aider | P1 | DONE | T005
- [T015] Unit tests for item matching | aider | P1 | DONE | T006
- [T016] Write unit tests for AI extraction | aider | P1 | DONE | T003,T004
- [T017] FaturaImportLog status tracking and error logging | aider | P1 | DONE | T001
- [T018] Code review pass | claude-code | P1 | DONE | T012
- [T019] Google Gemini AI provider | opencode | P2 | DONE | T003
- [T020] Performance: batch item matching caching | orchestrator | P2 | DONE | T006
- [T021] Fix P0 bugs BUG-1/BUG-2/BUG-3 in import_wizard.py | orchestrator | P0 | DONE | T018
- [T022] Fix COR-1 (None tax_id guard) + COR-2 (items vs line_items key) | aider | P1 | DONE | T021
- [T023] Fix SEC-1/SEC-2 | orchestrator | P1 | DONE | T021
- [T024] PDF text extractor + DeepSeek structured extraction | aider | P0 | DONE | none
- [T025] Gemini Flash vision provider (image/scan fallback) | opencode | P0 | DONE | T024
- [T026] Smart provider routing + extraction prompt template | aider | P0 | DONE | T025
- [T027] Add DeepSeek provider fields to FaturaSettings DocType | aider | P0 | DONE | T024
