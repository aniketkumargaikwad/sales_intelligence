# Evals

Golden cases for every LLM-backed skill (brief §10). Each case gives the input a skill was run on
and the properties its output must have. Check an output with:

```bash
uv run python -m si eval evals/<skill>/cases/<case>.yaml offers/<slug>
```

Each case names a `fixture`, a committed output known to be good. `tests/test_evals.py` runs
every case against its fixture, so a change to the schema, the checker or a committed offer
that breaks an expectation fails CI.

To evaluate a skill change: run the skill in Claude Code on the case's `input` into a scratch
offer folder (for example `offers/_eval-run/`), then run `si eval` against that folder.
