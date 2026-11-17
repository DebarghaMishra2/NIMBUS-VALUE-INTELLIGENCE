# Nimbus Group — Enterprise RAG Value Intelligence Assistant

**HCLTech | Future Ready AI Engineer Hackathon — Mail 2b**

A runnable prototype for AI portfolio management and executive reporting. It combines a deterministic Python scorecard with charter retrieval and a grounded assistant. It implements the HCLTech FR-01 through FR-10 capabilities described in the supplied participant brief.

> The supplied Nimbus practice datasets are synthetic. Do not present them as actual Nimbus Group financial outcomes.

## Features

- Select either the curated 8-initiative practice dataset (`nimbus_8`) or the 40-initiative scale dataset (`nimbus_40`). The 40-initiative dataset already includes the original 8 plus 32 generated initiatives; the folders must not be concatenated.
- Ingest CSV, Excel, Markdown, PDF and DOCX sources.
- Normalize initiative IDs, dates, numeric strings, metric aliases, financial measure names and USD-thousands units.
- Remove exact duplicate usage rows, flag missing weeks and invalid WAU, roll up monthly cost records, and ignore supplied `reported_roi_pct` values.
- Create an auditable change log with source, record, field, old/new values, effect and severity.
- Calculate the seven required metrics and Green/Amber/Red status deterministically in Python.
- Extract and chunk charters with initiative, source filename, section and page metadata.
- Create vector representations and BM25 index; use reciprocal rank fusion for hybrid retrieval. Sentence Transformers dense embeddings are used when installed; otherwise a TF-IDF vector fallback keeps the app runnable.
- Route numeric, narrative and hybrid questions to the right evidence path.
- Cite source filenames and sections; show page numbers where available.
- Apply the required no-evidence fallback, personal-data refusal and planted prompt-injection protection.
- Generate a weekly executive report with portfolio summary and attention priorities.
- Export scorecard, change log and weekly report.

## Quick start (macOS / Linux)

1. Unzip the project folder.
2. Open Terminal and `cd` into the project folder.
3. Run:

```bash
chmod +x scripts/run.sh
./scripts/run.sh
```

4. Open `http://127.0.0.1:8000` in your browser.
5. Select `8 initiatives · Development` and click **Process dataset**. Then use the scorecard, assistant, report and data-quality tabs.
6. Switch to `40 initiatives · Scale` and click **Process dataset** to demonstrate the larger dataset.

The `run.sh` script creates `.venv`, installs `requirements.txt` and starts FastAPI on port 8000. If port 8000 is occupied, stop the old process (`lsof -nP -iTCP:8000 -sTCP:LISTEN`, then `kill <PID>`) or run `PORT=8001 ./scripts/run.sh`.

## Windows quick start

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Optional dense sentence-transformer embeddings

The base installation uses TF-IDF vector embeddings as a local fallback. For dense semantic embeddings using `all-MiniLM-L6-v2`, install:

```bash
pip install -r requirements-semantic.txt
```

Set `EMBEDDING_BACKEND=sentence-transformers` in your environment to require the dense model. The first model load may download model weights; allow network access or pre-cache the model. Without this extra, BM25 + TF-IDF vectors + RRF still work locally.

## Optional hosted LLM

The prototype works without an API key in deterministic, grounded extractive mode. This ZIP includes a blank `.env` file in the project root (the same folder as `README.md`). Open `.env` (not `.env.example`) and paste your newly generated key into `GROQ_API_KEY`. If `.env` is missing, create it by running `cp .env.example .env`. The application defaults to `https://api.groq.com/openai/v1` and `openai/gpt-oss-120b`. Alternatively, set all three canonical variables: `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`. Restart the server after changing `.env`. The `/api/health` endpoint reports which settings are missing without exposing the key. It also reports `llm_key_loaded: true/false` without returning the key. Open `http://127.0.0.1:8000/api/llm/test` to test an actual provider request. Chat responses also include `llm_status` so a rejected output, timeout or provider HTTP error is distinguishable from missing configuration. The assistant may repeat only initiative IDs present in the verified scorecard; all other numeric figures stay in the deterministic metrics panel.

Never commit `.env` or expose a key in browser JavaScript. Numeric figures remain sourced from the Python scorecard; the optional LLM is instructed not to generate numeric figures and to treat retrieved charter content as untrusted data.

## Troubleshooting

- **Chat shows HTTP 500:** the API now recursively converts Pandas/NumPy missing and non-finite values (NaN/Infinity) to JSON `null`. Restart with the latest project files. If an unexpected exception remains, the backend terminal logs the traceback and the UI shows the API error detail.
- **Port 8000 is occupied:** `scripts/run.sh` automatically tries the next available port when the default port is busy. If you explicitly choose a port, use `PORT=8001 ./scripts/run.sh` (or another free port). The startup line prints the actual URL.
- **LLM shows not configured:** edit the root `.env` file and set `GROQ_API_KEY`; restart the server. Do not edit `.env.example` and never commit `.env`.
- **LLM connection test fails:** open `/api/llm/test` and inspect the returned HTTP status/error. A healthy app endpoint does not by itself prove that the provider key/model works.
- **Retrieval vectors show `tfidf-fallback`:** the default installation uses a local TF-IDF vector fallback. To enable dense Sentence Transformer vectors, install `requirements-semantic.txt`, set `EMBEDDING_BACKEND=sentence-transformers`, then re-process the dataset.

## Evaluation

Run both dataset evaluations:

```bash
python -m evaluation.evaluate --dataset both
```

Or run a single dataset:

```bash
python -m evaluation.evaluate --dataset nimbus_8
python -m evaluation.evaluate --dataset nimbus_40
```

Run automated tests:

```bash
pytest -q
```

The evaluation script compares every required metric with `answer_key/expected_scorecard.csv` and runs functional checks for routing, missing evidence, personal-data fallback, prompt injection, hybrid answering and weekly report generation. Answer keys are used only by offline evaluation; the application ingestion and runtime paths do not read answer-key files.

## API endpoints

- `GET /api/health`
- `GET /api/datasets`
- `POST /api/ingest`
- `GET /api/portfolio?dataset_id=nimbus_8&as_of_date=2026-11-15`
- `GET /api/scorecard?...`
- `GET /api/data-quality?...`
- `GET /api/charters?...`
- `GET /api/assumptions`
- `POST /api/chat`
- `GET /api/weekly-report?...`
- `GET /api/download/scorecard.csv?...`
- `GET /api/download/change-log.csv?...`
- `GET /api/download/weekly-report.md?...`

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Metric definitions and benchmark assumptions

See `docs/METRIC_DEFINITIONS_AND_ASSUMPTIONS.md`. The default reporting date is 2026-11-15. Months live is elapsed days divided by 30.44. WAU change uses the first and latest available weeks in the supplied period. USD '000 is multiplied by 1,000. Monthly cost rows are summed to date. The precomputed ROI field is ignored.

## HLD and demo

- `docs/HLD.md` — architecture and end-to-end data flow.
- `HCL_REQUIREMENTS_TRACEABILITY.md` — mapping of FR-01 to FR-10 to implementation.
- `docs/GUARDRAILS.md` — grounding, no-answer and safety rules.
- `docs/LLM_SETUP.md` — provider key setup, connectivity test and troubleshooting.
- `docs/DEMO_SCRIPT.md` — demo flow and worked examples.

## Known limitations and honest scope

- The datasets are synthetic and small; this prototype demonstrates correctness, not production-scale performance.
- Dense Sentence Transformer embeddings require the optional package and model weights. TF-IDF vectors are used otherwise.
- A hosted LLM is optional; when not configured, the app uses deterministic, extractive grounded responses.
- The retrieval evaluation in the included script is a functional smoke evaluation. A human-judged relevance set is needed to report credible Precision@K, Recall@K and MRR values.
- No FX conversion is implemented; the supplied data states USD.
- The application generates recommendations for human review only. It does not approve investments, modify original source files or execute business decisions.
- The monthly-versus-cumulative financial reporting clarification is documented in the assumptions file and should be confirmed before production use.

## Repository layout

```text
app/                 FastAPI, cleaning, scorecard, RAG, assistant, reporting
frontend/            Static responsive web interface
practice_data/data/  8 curated initiatives plus answer key
practice_data/data_scale_40/ 40 initiatives plus answer key
practice_data/scripts/ Original practice-data generator and reference verifier
docs/                HLD, assumptions, guardrails, demo script
evaluation/          Reproducible evaluation script and generated results
tests/               Automated requirements tests
storage/             Generated cleaned data, indexes and scorecards
```

### Enabling dense semantic embeddings for the final hackathon demo

The default installation supports a local TF-IDF vector fallback so the app starts even without model weights. To enable the Sentence Transformer embedding model used by the RAG branch, run:

```bash
pip install -r requirements-semantic.txt
```

Then set `EMBEDDING_BACKEND=sentence-transformers` and restart the app. The first run may download model weights. The app reports the active backend after dataset processing.

## Source brief used

Implementation is based on the **Enterprise RAG Value Intelligence Assistant** use case in the supplied HCLTech Future Ready AI Engineer Hackathon email brief (Mail 2b), not the separate Intelligent IT Ticket Analysis use case also quoted later in that email thread.
