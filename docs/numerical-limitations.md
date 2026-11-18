# Numerical and modelling limitations

The principal experiments illustrate strategic quoting incentives and test a fixed-belief approximation. The qualifications below define the scope of those results. The original scientific scripts are preserved; additive verification and execution records are described in [reproducibility.md](reproducibility.md) and [the results index](../results/README.md).

## Equilibrium computation

`solve_side()` returns its last iterate after at most 120 best-response iterations. The original function does not report iteration-limit exhaustion. Its bisection interval is fixed at `[-10, 10]`, and endpoint signs are not checked internally. Successful execution therefore does not by itself establish convergence or root bracketing.

First-order and fixed-point residuals, finite-value checks, bracket checks, and iteration monitoring provide evidence for the tested configuration. Passing them does not prove accuracy for every parameter set. Changes to intensity parameters or inventory bounds require fresh checks.

For the submitted `Q=5`, 100-step configuration, **all 12 added diagnostic checks passed**. The [diagnostic record](../results/diagnostics.json) reports:

| Check or measure | Observed result |
|---|---|
| Side solves monitored | 202 |
| Maximum fixed-point iterations | 7, against a limit of 120 |
| Iteration-limit exhaustion | None |
| Maximum absolute first-order residual | `6.926713143166896e-9` |
| Maximum absolute fixed-point residual | `4.604316927725449e-11` |
| Root bracketing and finite outputs | Passed |
| Probability normalization and terminal condition | Passed |
| Quote monotonicity and symmetry | Passed |
| A rate probability bounds and inventory boundary rates | Passed |

These results address the silent-failure concern for the checked defaults without adding failure reporting to the preserved solver itself. Five [unit tests](../results/unit-tests.log) also passed, covering direct enumeration of extreme-inventory probabilities, a finite-difference intensity derivative, original source-byte preservation, the single-rival case, and an uninformative-observation posterior. Residual and consistency checks do not replace time-grid refinement or prove optimality over arbitrary strategies.

The time method is backward-in-time **explicit Euler**, with first-order discretization error. Increasing the number of simulation substeps leaves the equilibrium solver's time grid unchanged. Historical refinement claims require their own settings and outputs; they must not be inferred from a completed baseline run.

The max/min rival-inventory mapping assumes that ask quote distances decrease and bid quote distances increase with inventory. Monotonicity passed across the submitted `Q=5`, 100-step grid. Other configurations require their own checks; coarse-grid numerical artifacts can invalidate the mapping.

## Execution approximation and inventory boundaries

The simulator uses `rate * dt` as an execution probability. It is a Bernoulli time-step approximation, not an exact continuous-time Poisson event simulation.

- At most one execution per side occurs within a substep; multiple same-side arrivals are omitted.
- Bid and ask hits may occur together, with both rates and quotes calculated from the pre-substep state.
- Rates are recomputed after a substep, not after each individual execution within it.
- Inventory eligibility masks disable selling at `-Q` and buying at `+Q`. The one-hit-per-side update respects those bounds for valid initial states.
- If `rate * dt` exceeds one, the comparison with a uniform draw silently saturates the hit probability. Values below one still require a small-step accuracy assessment.

Maximum rate-times-step diagnostics and refinement results should be interpreted separately. A valid probability bound does not establish negligible discretization bias.

The completed full reproduction recorded the following maxima with `dt=0.001`:

| Scenario | Maximum rate times step | Scope |
|---|---:|---|
| A baseline, `c=0` | 0.077400212125 | All inventory states and simulation policy grid points in the rate tables |
| A most aggressive tested shift, `c=-0.20` | 0.126803377404 | Largest table value across all tested shifts |
| B explicit game | 0.088284893698 | Largest observed value over the executed paths and substeps |

These values are below one, so this check found no probability saturation in the A tables or visited B states. The largest A probability is about 0.127, which is not negligible; the first-order approximation can still contribute bias. The B observation is not a bound over every possible unvisited joint inventory state. Simultaneous bid/ask hits occurred in the run, and recorded inventories stayed within `[-5,5]`. Full-precision values and observation counts are retained in [the full-run summary](../results/full/summary.json).

## Explicit-game and belief consistency

The equilibrium construction uses fixed rival-state probabilities. In Experiment B, inventories interact and their distributions evolve. The empirical histogram is an ensemble summary, not a posterior conditioned on a maker's entire private observation history.

The prior helper removes cases where no rival can quote an ask **or** no rival can quote a bid, then normalizes. The plotted simulation records retain observations where a best rival ask is available. Thus, their conditioning differs. Record retained and excluded counts when interpreting the comparison, especially at the initial time.

When all rivals are unavailable on one side, B substitutes a quote distance of `10.0`. The simulator assigns per-maker arrival intensities; it does not implement a full exchange order book or allocate a single shared order stream across makers.

Belief-distribution differences and objective gaps may coexist without identifying a causal payoff cost of belief drift. Different boundary conventions, time approximations, and the evolving joint state can also matter. The unresolved B discrepancy should not be explained entirely by one graph.

For `q0=0`, the full reproduction gave an A mean of 9.548654250 (standard error 0.009316322) against theory 9.535126740. B gave 9.569540814 (standard error 0.013362646), a gap of +0.034414073, about 2.575 standard errors. These reproduce the report's rounded baseline values but do not resolve the B discrepancy. The best-ask record at `t=0.5` retained 19,999 of 20,000 paths; one path had no rival ask at that recording time. The conditioning distinction is therefore present in the recorded evidence, even when its numerical effect is small.

## Scope of the deviation test

Experiment A adds the same constant `c` to both quote distances. At a fixed state, the full bid-ask spread changes by `2c`. It tests six nonzero shifts for three starting inventories under the fixed-belief environment.

Evidence against this family of deviations does not establish optimality against arbitrary time-dependent or inventory-dependent policies, independent bid/ask changes, or deviations within B. The zero difference at `c=0` is constructed by comparing the baseline with itself.

The plotted bars equal twice the standard error of paired pathwise differences. They are pointwise Monte Carlo uncertainty measures. They neither provide a simultaneous guarantee across comparisons nor include solver or simulation discretization error.

## Bayesian extension and cache policy

The two main figures do not use posterior updates. The standalone Bayesian script studies a single noisy observation using a prior-equilibrium likelihood. Its object called an oracle solves fixed-belief, point-mass cases for rival inventory extremes. It does not solve a complete-information dynamic game over all makers' evolving inventory vectors. Solving with posterior marginals alone also does not verify a full Bayesian Nash equilibrium with consistent information and beliefs for every player.

The Bayesian main routine reuses `oracle_ask.npy` if present without checking its parameters or source revision. No pre-existing oracle cache is needed for the principal simulation figures. For a separate Bayesian run, use a fresh isolated directory and generate the cache there; keep it with a configuration manifest and source hashes if it is retained. Do not reuse a cache across configurations merely because its filename matches. This policy preserves the original implementation while preventing accidental stale-cache use.

## Parameter changes and interpretation

`joint_max_min()` relies on the global state count in `mm_bayes.py`. Changing `Q` in one caller is insufficient. The unused `paper_beliefs(Q)` helper is designed for `Q=10`; it is generally not normalized for other bounds.

The payoff is terminal cash plus marked-to-market inventory less penalties. It includes the value of the initial inventory endowment, so absolute objectives for different `q0` values are not directly comparable as trading profits from equal initial wealth.

All observations are synthetic. No order-book dataset, informed-trader adverse-selection model, or empirical calibration is claimed. The benchmark uses `0.5*Lam*exp(-a*d)`, while the implemented competitive intensity tends to `Lam*exp(-a*d)` as the rival distance tends to infinity. Removing rivals in B is therefore not automatically the same as the chosen benchmark comparison.

The source paper motivates the model and proves results under its assumptions; those theorems do not certify a particular discretized implementation. [Luo and Zheng, 2021](https://doi.org/10.1007/s13235-020-00373-w)
