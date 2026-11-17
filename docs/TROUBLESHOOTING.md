# Troubleshooting

## Chat request returns HTTP 500

This release applies recursive JSON sanitization to chat, portfolio, scorecard and data-quality responses. Pandas/NumPy missing or non-finite values are returned as JSON `null` rather than causing JSON serialization errors. Restart the updated backend after replacing project files. If an unexpected exception remains, inspect the backend terminal traceback; the chat endpoint logs the full server-side exception and returns a safe diagnostic message to the browser.

## Port is already in use

The startup script checks the selected port. When the default port 8000 is busy and no explicit `PORT` is set, it tries subsequent ports. It prints the actual URL. To select a port explicitly:

```bash
PORT=8001 ./scripts/run.sh
```

## LLM provider is not configured

Edit `.env` in the project root (beside `README.md`), not `.env.example`:

```dotenv
GROQ_API_KEY=your_new_key_here
```

For Groq, the app defaults to the OpenAI-compatible API URL and `openai/gpt-oss-120b` model. Restart the backend after editing `.env`. Never commit `.env` or share screenshots that expose the key. If a key has been exposed, revoke it and create a new one.

Use `GET /api/health` to confirm that configuration loaded and `GET /api/llm/test` to test an actual provider completion. The health endpoint never returns the key value.

## LLM works but an answer is deterministic

Check the `llm_status` field in the `/api/chat` response. Values such as `not_configured`, `http_error_401`, `http_error_429`, `timeout`, `rejected_numeric_output`, or `rejected_unverified_identifier` explain why the app used its deterministic grounded answer instead. Numeric values always remain sourced from the deterministic scorecard.

## Retrieval vectors show `tfidf-fallback`

This is the lightweight default and still supports hybrid BM25 + vector ranking. For dense semantic embeddings, install:

```bash
pip install -r requirements-semantic.txt
```

Set `EMBEDDING_BACKEND=sentence-transformers` in `.env`, restart and re-process the selected dataset. The model may need to download on first use.
