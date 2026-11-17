# Changelog

## Rectified release

- Added recursive strict-JSON sanitization for NumPy/Pandas values, including NaN, Infinity, `pd.NA`, `NaT`, timestamps and nested structures.
- Applied response sanitization to chat, portfolio, scorecard and data-quality API responses.
- Added safe chat exception logging and a user-facing diagnostic message instead of an opaque HTTP 500 page.
- Allowed grounded narrative answers to repeat initiative identifiers when those identifiers are supported by retrieved charter evidence, not only by scorecard metrics.
- Improved frontend display of API error details.
- Improved startup port handling and prints the actual application URL.
- Added API regression tests for the previous chat 500 path, both datasets, non-finite response values, LLM-grounded hybrid responses and all principal endpoints.
- Added troubleshooting documentation.
- Included a blank root `.env` template; no API key is bundled.

## Scope retained

The project remains the HCLTech Mail 2b **Enterprise RAG Value Intelligence Assistant**. The supplied practice data remains synthetic. Metric calculations remain deterministic; the LLM only explains the governed scorecard and retrieved charter evidence.
