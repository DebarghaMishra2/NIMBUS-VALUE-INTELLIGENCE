# LLM setup (Groq or another OpenAI-compatible provider)

## 1. Use the correct file

The project ZIP includes a blank `.env` file in the project root. It is beside `README.md` and `.env.example`. Edit `.env`, **not** `.env.example`.

For Groq, configure only this key (the app supplies the default API URL and model):

```dotenv
GROQ_API_KEY=gsk_your_new_key_here
```

The default is `https://api.groq.com/openai/v1` with model `openai/gpt-oss-120b`. If you use another Groq model, set `LLM_MODEL` too.

Alternatively, for another OpenAI-compatible provider, set all three: `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`.

## 2. Restart the backend

Stop the current server with `Ctrl+C`, then run:

```bash
./scripts/run.sh
```

If port 8000 is occupied, inspect the process with:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Stop the old process with `kill <PID>`, or use another port:

```bash
PORT=8001 ./scripts/run.sh
```

When using port 8001, open `http://127.0.0.1:8001`.

## 3. Verify configuration and provider access

Open `http://127.0.0.1:8000/api/health`. The expected fields when configured are:

```json
{
  "llm_enabled": true,
  "llm_configured": true,
  "llm_key_loaded": true,
  "llm_missing_settings": []
}
```

Then open `http://127.0.0.1:8000/api/llm/test`. This sends an actual small completion request to the configured provider. A successful health check means configuration loaded; a successful provider test confirms the API request worked.

## 4. Security

- Never put your real key in `.env.example`.
- Never commit `.env` or paste the key into frontend code. `.env` is listed in `.gitignore`.
- If a key has appeared in a screenshot, chat, commit or shared file, revoke it and generate a new key.
