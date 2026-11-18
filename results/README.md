# Recorded results

These files contain evidence actually produced during repository preparation on 18 November 2026. The original three scientific scripts were preserved unchanged. Values below are objective values, including inventory endowment and penalties, not simply cash profit.

## Completed executions

| Run | Execution | A / B paths | Status | Recorded elapsed time |
|---|---|---|---|---|
| Quick | Original `simulate_game.py --quick`, executed in an isolated output directory | 4,000 / 2,000 | Completed, exit code 0 | 17.42 seconds process wall time |
| Full | Original main routine, invoked through the additive evidence-export runner | 40,000 / 20,000 | Completed, exit code 0 | 34.90 seconds runner elapsed time |

Measured times are specific to the recorded Windows environment; instrumentation and process startup differ between these executions. They are not hardware-independent performance guarantees.

## Full-run baseline objectives

| Experiment | Initial inventory | Fixed-belief theory | Simulated mean | Standard error | Mean minus theory |
|---|---:|---:|---:|---:|---:|
| A | -3 | -50.594280 | -50.576786 | 0.009329 | +0.017494 |
| A | 0 | 9.535127 | 9.548654 | 0.009316 | +0.013528 |
| A | +3 | 69.405720 | 69.419052 | 0.009347 | +0.013332 |
| B | -3 | -50.594280 | -50.566135 | 0.013405 | +0.028145 |
| B | 0 | 9.535127 | 9.569541 | 0.013363 | +0.034414 |
| B | +3 | 69.405720 | 69.437265 | 0.013371 | +0.031545 |

These rounded baseline values reproduce the corresponding supplied report table. The B/theory comparison juxtaposes an explicit evolving-inventory simulation with a fixed-belief value function. It is not a direct estimate of the causal cost of belief drift. Sampling standard errors do not include solver or simulation bias.

For all three inventories, every tested nonzero constant shift has a negative full-run mean payoff difference. See [deviations.csv](full/deviations.csv) for the paired standard errors rather than reading exact values from the PNG.

## Full-run belief records shown in the report figure

The figure uses only the reference initial-inventory-zero records:

| Time | Total-variation distance from assumed distribution | Retained ask observations | Excluded observations with no rival ask |
|---|---:|---:|---:|
| 0.0 | 0.004162 | 20,000 | 0 |
| 0.5 | 0.097912 | 19,999 | 1 |
| 0.9 | 0.055443 | 20,000 | 0 |

This is close initial agreement with finite sampling error, followed by a larger mid-horizon discrepancy. The report's approximate time-zero distance of 0.03 does not describe this reproduced full run. Records for all three initial inventories are retained in the JSON and CSV evidence; only inventory zero is plotted by the original code.

## Retained files

| Location | Contents |
|---|---|
| [quick/console.log](quick/console.log) | Original quick-run console output, with the source's printed rounding. |
| [quick/execution.json](quick/execution.json) | Original quick command, working directory, source revision, elapsed time, and exit code. |
| [quick/fig_sim_deviation.png](quick/fig_sim_deviation.png), [quick/fig_sim_belief.png](quick/fig_sim_belief.png) | Quick-run generated figures, distinct from the report references. |
| [full/console.log](full/console.log) | Preserved original console output during the instrumented full run. |
| [full/manifest.json](full/manifest.json) | Command, source and helper hashes, versions, settings, seeds, runtime, and generated-image hashes. |
| [full/summary.json](full/summary.json) | Full-precision baseline and deviation statistics, belief counts, and passive simulation observations. |
| [full/experiment_A.csv](full/experiment_A.csv) | Baseline theory, mean, standard error, and discrepancies. |
| [full/experiment_B.csv](full/experiment_B.csv) | Explicit-game means, standard errors, and comparisons. |
| [full/deviations.csv](full/deviations.csv) | Paired payoff differences for every tested shift and starting inventory. |
| [full/beliefs.csv](full/beliefs.csv) | Best-ask rival inventory frequencies, denominators, and distances. |
| [full/fig_sim_deviation.png](full/fig_sim_deviation.png), [full/fig_sim_belief.png](full/fig_sim_belief.png) | Newly generated full-run images. They do not replace the selected report PNGs in `figures/`. |

The numerical diagnostics, environment reconciliation, and image comparisons are described in [reproducibility](../docs/reproducibility.md). Historical grid-refinement and standalone Bayesian results were not recovered as original saved logs and are not presented here as reproduced results.

## Verification outcomes

- [Numerical diagnostics](diagnostics.json): all 12 checks passed for the default configuration. Across 202 solver calls, no fixed-point limit was exhausted; at most seven iterations were used. Maximum first-order residual: 6.93e-9. Maximum fixed-point residual: 4.60e-11.
- [Unit-test log](unit-tests.log): five tests passed.
- [Full-run figure comparison](full/figure-comparison.json): both report images reproduced exactly at decoded RGBA pixel level, with zero different pixels; PNG bytes differ.
- [Environment reconciliation](environment-reconciliation.json): active package versions remained unchanged after hiding global site packages. The updated runner's clean-environment quick repeat reproduced the untouched quick PNG bytes exactly.

## Interpreting passive observations

The maximum A arrival probability bounds over all inventory/time table entries are about 0.0774 at the baseline and 0.1268 for shift -0.20. The maximum observed B probability is about 0.0883. All are below one; this does not show that the time-step approximation has negligible bias. Bid and ask hits sometimes occur within the same substep, and the no-rival-quote fallback is exercised.

In `observed_simulation`, A maxima are table bounds, while B maxima are observed along simulated states. The A zero-shift trace aggregates the initial baseline evaluation and the repeated zero-shift evaluation performed by the original experiment. Count totals for that trace therefore include two source calls. These details do not change the paired payoff statistics.
