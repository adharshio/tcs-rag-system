# Testing & Evaluation (Team 5, Person A)

Golden test set and evaluation script for the Campus Placement RAG assistant.

## Files

| File | Purpose |
|---|---|
| `golden_test_set.json` | 50 test questions with expected answers, sources and refusal rules |
| `evaluate_rag.py` | Runs the questions against `/api/chat` and computes metrics |
| `requirements.txt` | Python dependencies |
| `results/` | Output of each run (CSV + summary JSON) |

## Quick start

```bash
pip install -r requirements.txt
python evaluate_rag.py --mock                        # check the script works
python evaluate_rag.py --url http://localhost:8000   # run against the real backend
```

Useful options: `--variants` (also run rephrasings), `--only-verified`,
`--category eligibility`, `--token <JWT>`, `--out results/run_02_after_fix`.

## API contract expected from the backend (Team 3)

`POST /api/chat`

```json
{"question": "...", "history": [{"role": "user", "content": "..."}]}
```

Response:

```json
{"answer": "...", "sources": ["Placement Policy 2026"],
 "retrieved_chunks": [{"source": "Placement Policy 2026", "text": "..."}]}
```

`history` and `retrieved_chunks` are optional. `retrieved_chunks` gives a more accurate retrieval score.

## Metrics

- Retrieval hit rate: expected source found in retrieved chunks or cited sources
- Answer correctness: fraction of expected answer points found in the answer
- Refusal accuracy: refuses when it should; false refusal rate when it shouldn't
- Forbidden content: leaked or invented text listed in `must_not_contain`
- Latency: p50 and p95

## Status of the golden set

Expected values are placeholders marked `[VERIFY]` until checked against the real
placement documents. An entry is only final when `"verified": true`.
Do not edit questions to fit results. Fix genuine mistakes only.

## Workflow

1. Run the evaluation, open the CSV, filter `outcome = FAIL`.
2. Fill the `failure_tag` column (retrieval_miss, bad_chunking, prompt, hallucination, wrong_refusal).
3. Send failures to the owning team, and re-run after their fix with a new `--out` name.
4. Keep the first and last `*.summary.json` for the before/after slide.
