# Evaluation summary — HCLTech Enterprise RAG Value Intelligence Assistant

Evaluation run: local deterministic application pipeline, 17 November 2026 benchmark data.

## Results

| Check | `nimbus_8` | `nimbus_40` |
|---|---:|---:|
| Initiatives in scorecard | 8 | 40 |
| Planted issue catalogue entries supplied | 17 | 138 |
| Row-level change-log entries generated | 129 | 671 |
| Charter chunks extracted | 63 | 316 |
| Maximum absolute scorecard difference vs answer key | 3.64e-12 | 3.64e-12 |
| G/A/R status match | Pass | Pass |
| Functional smoke checks | 8/8 pass | 8/8 pass |
| Exact source-and-section hit rate on 8 manually curated queries | 100% | 100% |
| Mean reciprocal rank on that section-aware query set | 1.00 | 1.00 |

The numeric scorecard comparison covers months live, adoption, WAU change, ROI, average monthly benefit, payback months and run-rate versus plan. The maximum error is far below the HCL benchmark tolerance of 1e-6. Status labels also match the supplied answer keys.

## Functional checks

- Numeric question routed to deterministic analytics.
- INIT-003 risk question returned the exact required no-evidence fallback.
- Personal phone-number request returned the exact required fallback.
- INIT-005 planted prompt-injection instruction was not present in the model-context chunk or answer.
- Hybrid question for INIT-005 used both scorecard metrics and charter evidence.
- Weekly executive report generated.
- Charter chunks and metadata were created.
- Eight manually curated, section-aware questions retrieved the expected charter filename and section; this is a small targeted smoke set, not an unbiased corpus-wide retrieval benchmark.

All seven checks passed for both datasets.

## Retrieval implementation observed in this evaluation

The current runtime did not have `sentence-transformers` installed, so the test run used scikit-learn TF-IDF vector representations plus BM25 and reciprocal rank fusion. The package includes `requirements-semantic.txt` for dense Sentence Transformer embeddings (`all-MiniLM-L6-v2`) when internet/model caching and the larger ML dependency are available. The exact embedding backend is displayed by the application after processing.

## Important evaluation limitations

- The current RAG checks are functional smoke tests using eight manually curated section-aware questions from the supplied charters. The exact source-and-section hit rate and MRR are not comparable to a broad unbiased retrieval benchmark. Do not claim corpus-wide Precision@K or Recall@K without building and judging a larger relevance set.
- The optional hosted LLM path was not exercised because no provider API key was supplied. The shipped app remains usable in deterministic grounded mode.
- The source data is synthetic practice data, not actual Nimbus Group outcomes.
- The 40-initiative dataset is a demonstration scale set, not proof of production-scale load capacity.
