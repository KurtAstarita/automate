# Ghost testing

## Run locally

Use the same safety flags as CI:

```bash
GHOST_MODE=true DRY_RUN=true ALLOW_SIDE_EFFECTS=false \
python scripts/ghost_harness.py --scenario happy_path --output-dir ghost-artifacts
```

Swap `happy_path` for any fixture in `tests/fixtures/ghost_scenarios/`, including `adversarial_input`.

## Refresh golden snapshots intentionally

Golden baselines live under `tests/golden/ghost/`.

Refresh one scenario:

```bash
GHOST_MODE=true DRY_RUN=true ALLOW_SIDE_EFFECTS=false \
python scripts/ghost_harness.py --scenario happy_path --update-goldens --output-dir ghost-artifacts
```

Review the updated checked-in golden file before committing it.

## Why the quality gate fails

The ghost harness fails the PR check when any of these happen:

- contract validation fails, including a missing or mismatched `contract_version`
- the current normalized snapshot differs from the checked-in golden unexpectedly
- a stage `fallback_rate` increases above the baseline threshold
- a stage `missing_required_field_rate` increases above the baseline threshold

Actionable details are written to:

- `ghost-artifacts/<scenario>/golden_diff_report.json`
- `ghost-artifacts/<scenario>/reliability_metrics.json`
- `ghost-artifacts/<scenario>/quality_gate_report.json`
- `ghost-artifacts/<scenario>/ghost_summary.md`
