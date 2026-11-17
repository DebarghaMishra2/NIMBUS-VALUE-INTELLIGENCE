# HCLTech FR-01 to FR-10 implementation traceability

| HCL functional requirement | Included implementation | Verification / UI |
|---|---|---|
| FR-01 Understand and document | `docs/METRIC_DEFINITIONS_AND_ASSUMPTIONS.md` | Definitions, assumptions and one material client clarification question; Assumptions UI tab |
| FR-02 Load and clean data | `app/cleaning.py` | Change log records rule, source, row, old value, new value and effect; Data Quality UI tab |
| FR-03 Compute scorecard | `app/scorecard.py` | Deterministic calculations; `/api/scorecard`; answer-key comparison in `evaluation/evaluate.py` |
| FR-04 Index project charters | `app/documents.py`, `app/retrieval.py` | Markdown/PDF/DOCX extraction, section-aware chunks, metadata, embeddings or TF-IDF vectors, persisted index artifacts |
| FR-05 Route user questions | `app/assistant.py` | Analytics, narrative and hybrid routing; `/api/chat` |
| FR-06 Generate grounded answers | `app/assistant.py` | Scorecard source references and filename/section/page citations |
| FR-07 Handle missing evidence | `app/assistant.py` | Required exact fallback: `I do not have that in the data provided.` |
| FR-08 Apply guardrails | `app/assistant.py`, `app/documents.py`, `docs/GUARDRAILS.md` | Personal-data refusal; embedded instruction neutralisation; no LLM numeric generation |
| FR-09 Produce weekly reporting | `app/reports.py` | `/api/weekly-report`; Markdown download; status and attention highlights with sources |
| FR-10 Simple interface | `frontend/index.html`, `app/main.py` | Scorecard, source viewing, assistant, assumptions, change log and weekly report |

## HCL expected submissions

- Data-quality and assumptions log: included in UI and downloadable CSV; definitions and clarification question are documented.
- Computed value scorecard: visible in UI and downloadable CSV.
- Grounded assistant: supports analytics, narrative and hybrid questions with citations and no-answer fallback.
- Weekly executive report: generated in UI and downloadable as Markdown.
- Guardrail demonstration: included in `docs/DEMO_SCRIPT.md` and automated tests.
- Evaluation summary: generated in `evaluation/evaluation_nimbus_8.json` and `evaluation/evaluation_nimbus_40.json` by the evaluation command.
- Technical documentation: README, HLD, assumptions, guardrails and demo script are included.
