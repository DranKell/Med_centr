# Dental AI Platform Project Instructions

## Project scope
- This is an internal-document drafting tool for a small dental clinic.
- SOPs and checklists are drafts only. Never imply that generated content is approved, legally compliant, or clinically validated.
- Do not create patient records, patient-specific medical advice, diagnoses, prescriptions, or invented clinical history.
- Reflect the actual single-dentist staffing model. Do not assume assistants, nurses, contractors, equipment, licenses, or services exist unless project data says so.

## Official legal sources
- For normative references, use only citations entered by the user or records returned by the official Russian legal publication portal (`publication.pravo.gov.ru`) and included in the current request.
- Never invent or autocomplete legal act names, numbers, dates, clauses, publication IDs, or URLs. Do not treat model knowledge or a general web search as a verified legal source.
- Search results are candidate records only. Preserve their official title, publication ID/date, and source URL; state that applicability and current validity must be checked by the clinic's responsible representative.
- If the official search returns no matches, say so. If it is unavailable or cannot be parsed, say it is unavailable. Never silently leave normative references blank or fabricate replacements.
- Keep user-supplied citations distinguishable from search results and mark them as requiring verification.

## AI generation and safety
- Keep the required SOP JSON keys stable: `scope`, `normative_refs`, `terms`, `responsibilities`, `procedure`, `quality_control`, and `documentation`.
- Validate and normalize untrusted model output before returning it to the frontend. Escape user/model content before inserting it into HTML.
- Do not disable TLS certificate verification. Configure an explicitly trusted certificate bundle when required.
- Do not log or expose API keys, IAM tokens, credentials, or personal data.

## Working in this repository
- Follow the existing FastAPI, Pydantic, SQLAlchemy, plain HTML/CSS/JavaScript, and unittest patterns. Keep changes focused and avoid adding dependencies when the standard library suffices.
- Run backend tests from `backend` with `venv\\Scripts\\python.exe -m unittest test_release_safety.py`.
- Keep `.env`, caches, generated probe scripts, database files, and unreviewed certificate material out of Git. Stage only files related to the requested change.