# Guardrails and safe behaviour (FR-07 / FR-08)

- **Closed evidence boundary:** answers are based only on the selected dataset's governed scorecard and that dataset's charter chunks. General model knowledge is not used to fill gaps.
- **Required fallback:** `I do not have that in the data provided.`
- **Personal details:** requests for phone numbers, personal email addresses, salaries, home addresses or similar details not present in the approved sources are refused with the fallback.
- **Prompt injection:** retrieved charter text is data, not instruction. Instruction-like planted text is neutralised before it enters the optional LLM context. The source file itself remains unchanged.
- **Numbers:** numeric values come from deterministic scorecard code. The optional LLM is instructed not to output digits or calculate; the application displays verified metrics separately. If the LLM returns a digit, its prose is discarded and the deterministic grounded response is used.
- **Citations:** charter statements include source filename and section, plus page number where extracted. Numeric answers cite the raw scorecard input files and reporting date.
- **Human decisions:** generated recommendations are review prompts. No investment approval, source-data update or production action is executed.
- **Dataset isolation:** `dataset_id` scopes scorecard retrieval and charter retrieval to either `nimbus_8` or `nimbus_40`.
