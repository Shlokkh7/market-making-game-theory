# Reproducibility record

## Evidence categories

- **Completed execution:** a program finished successfully and its actual output was retained.
- **Reproduced numerical result:** a specified value or comparison was independently generated during preparation; this does not alone establish accuracy of the continuous-time model.
- **Historical result:** a claim in the supplied report or earlier discussion without a corresponding newly reproduced experiment or recovered original log.
- **Unresolved / not tested:** the available evidence is insufficient or that experiment was not performed.

## Scientific source preservation

The three original scientific scripts and selected report figures were committed in the local source-preservation snapshot `e654e6a16150152ce09a65b3da704bdb4e2c2226`. Per-file SHA-256 values in [provenance](provenance.md) identify the exact source independently of Git history. `.gitattributes` prevents newline conversion of those three scripts on checkout.

The additive runner invokes the original main routine and observes returned arrays and selected execution state. It does not alter parameters, quote maps, execution rules, or random-number draws. The original quick command was also executed without those observations. The helper hash used for the full run is recorded in its manifest; later documentation or helper metadata changes must not be mistaken for changes to the scientific source.

## Execution results

| Item | Status and evidence |
|---|---|
| Imports and original quick command | Completed successfully; [quick log](../results/quick/console.log) and [execution record](../results/quick/execution.json). |
| Full A/B experiments | Completed successfully with 40,000 / 20,000 paths; [full manifest](../results/full/manifest.json), [full log](../results/full/console.log), and [numerical summary](../results/full/summary.json). |
| Baseline objective table in the supplied report | Reproduced at its printed precision by the full run; see [results index](../results/README.md). |
| Constant-shift deviation finding | Reproduced: all tested nonzero shifts have negative mean differences for all three starting inventories. Scope remains limited to the implemented fixed-belief experiment. |
| Report-image selection | Established by exact decoded RGB comparison of the supplied PNGs with embedded PDF images; [evidence](report-figure-evidence.json). |
| Newly generated full-run figures | Reproduced exactly at decoded RGBA pixel level for both figures, with zero differing pixels. PNG bytes differ; [comparison](../results/full/figure-comparison.json). |
| Default-configuration solver and rate diagnostics | All 12 checks passed; [diagnostics](../results/diagnostics.json). Across 202 solve calls, at most seven fixed-point iterations were used and none exhausted the limit. Maximum absolute first-order residual was 6.93e-9; maximum fixed-point residual was 4.60e-11. |
| Unit tests | Five passed; [test log](../results/unit-tests.log). |
| Added runner in an isolated environment | Quick repeat completed and reproduced the untouched quick-run PNG bytes exactly; see the environment reconciliation and retained repeat-run record. |
| Historical generating command, Python, and NumPy | Unresolved. New reproduction is separate evidence; image metadata alone does not establish the historical environment. |
| Historical solver-grid refinement | Not independently reproduced and original logs not recovered. |
| Standalone Bayesian Monte Carlo / oracle cache | Not run; unnecessary for the two principal figures. Cache policy is documented in [limitations](numerical-limitations.md). |
| Google Colab, Linux, and macOS execution | Not independently tested. Instructions are supplied for practical use, not marked as validated. |

Numerical diagnostic results and generated-image comparisons are retained as machine-readable evidence in `results/`. Passing these checks concerns the recorded default configuration, not arbitrary parameter choices or a proof about all possible deviations.

## Tested environment

The new runs imported Python 3.13.7, NumPy 2.5.5, and Matplotlib 3.10.8 on Windows 11 build 26300, AMD64. The runner records the processor, executable, command, and working directory in its manifest. The direct dependencies are pinned in `requirements.txt`.

The initial validation environment could see system-site distributions. Its full-run manifest records an older NumPy distribution entry even though the active imported module reports 2.5.5. The [environment reconciliation](../results/environment-reconciliation.json) records the package origins and confirms that active versions remain NumPy 2.5.5 and Matplotlib 3.10.8 after system-site visibility is disabled. A repeat quick run using the updated runner reproduces the untouched quick-run image bytes exactly. The original full manifest is preserved, including its shadowed metadata entry; the runner was subsequently improved to record distribution inventory without dropping duplicate versions. A local environment containing the direct pins is the intended setup for new users.

## Safe repeat execution

Run from the repository root after installing dependencies:

```text
python tools/run_experiments.py --quick --output-dir runs/quick
python tools/run_experiments.py --output-dir runs/full
python tools/verify_numerics.py --output runs/diagnostics.json
python -m unittest discover -s tests -v
```

Choose a new output-directory name for a new recorded run. The runner refuses a nonempty directory, avoiding accidental replacement of evidence. The report-reference PNGs are kept separately in `figures/` and are never overwritten by this arrangement.

The original `python simulate_game.py --quick` and `python simulate_game.py` commands still work; they write both PNG names to the current directory and do not preserve full-precision numerical tables automatically.

## Limits of the current evidence

Successful full execution establishes runnable code, saved numerical evidence, and the stated output comparisons. It does not establish negligible discretization bias, a proof of convergence for arbitrary parameters, full-game equilibrium against unrestricted deviations, a sequential Bayesian equilibrium, or empirical market validation. These questions remain distinct from software execution and are described in [numerical limitations](numerical-limitations.md).
