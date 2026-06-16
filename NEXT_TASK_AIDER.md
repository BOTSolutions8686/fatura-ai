# Next Task for Aider: T043 — Vision AI Extraction for Image Invoices
<!-- Written by Cowork Orchestrator at 2026-06-16 07:30 -->
**Priority:** P0
**Sprint:** 5
**Status:** ASSIGNED (Aider session active — DeepSeek may need direct prompting)

## Task
Add vision AI extraction to fatura_ai/helpers/ai_extraction.py.

Add `_extract_from_image(image_path, provider, settings)`:
- Use `pdf2image.convert_from_path(image_path, dpi=200)` to get page images
- For Gemini: call `gemini-1.5-flash` with image parts in message content
- For OpenAI: call `gpt-4o` with base64 image_url in message content
- For Anthropic: call `claude-3-5-sonnet-20241022` with base64 image source blocks
- Use `_build_extraction_prompt()` for the text prompt
- Return `_parse_extraction_response(response_text)` result

In `extract_invoice_data()`, after `detect_pdf_type()` returns `image`, call `_extract_from_image` instead of text extraction path.

Add `pdf2image>=1.17` to requirements.txt.

## Commit
```
git add fatura_ai/helpers/ai_extraction.py requirements.txt
git commit -m 'feat(T043): vision AI extraction for image invoices'
git push origin develop
```

Then update TASKS.md: move T043 to Done.

## Note for Aider
If DeepSeek asks for clarification, respond: 'Just implement _extract_from_image as described above. No clarification needed.'

