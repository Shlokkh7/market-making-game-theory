# Experiment configuration

The three Python files in the repository root are the preserved reference implementation. This page distinguishes their source-defined configurations from settings used in other historical report experiments. Actual execution environments, commands, runtimes, and verification outcomes are recorded in [reproducibility.md](reproducibility.md) and [the results index](../results/README.md).

## Main simulation

`simulate_game.py` builds a fixed-belief equilibrium and runs two experiments. Experiment A simulates a reference maker using belief-weighted rival quotes; Experiment B simulates four makers with evolving inventories.

| Setting | Value |
|---|---|
| Inventory bound | `Q = 5`; inventories are integers from -5 to +5 |
| Market makers in B | 4: reference maker 0 and 3 rivals |
| Rival initial prior | Weights proportional to `exp(-0.5 * (q / 2.0)**2)` on the bounded inventory grid |
| Reference initial inventories | `(-3, 0, 3)` |
| Initial cash | 0 |
| Initial reference price | `S0 = 20.0` |
| Trading horizon | `T = 1.0` |
| Arrival intensity scale | `Lam = 60.0` |
| Own-distance decay | `a = 2.0` |
| Relative-distance dependence | `k = 2.0` |
| Running risk coefficient | `gamma = 1.0` |
| Price volatility | `sigma = 0.01` |
| Terminal penalty | `liq * q_T**2`, with `liq = 0.1` |
| Equilibrium solver steps | 100; time-grid spacing 0.01 |
| Simulation substeps | 10 per solver interval; simulation increment 0.001 |
| Experiment A seed | 7 |
| Experiment B seed | 8 |
| Quote-distance shifts | `(-0.20, -0.10, -0.05, 0, 0.05, 0.10, 0.20)` |
| Best-ask rival recording times | 0.0, 0.5, 0.9 |

The prior's scale parameter is 2.0; truncation and discretization mean that its exact standard deviation need not equal 2.0. The generic `Params` class defaults to `Q=10`, but the simulation explicitly overrides it to `Q=5`.

| Mode | A paths per initial inventory and strategy | B paths per initial inventory |
|---|---:|---:|
| Quick: `python simulate_game.py --quick` | 4,000 | 2,000 |
| Full: `python simulate_game.py` | 40,000 | 20,000 |

Both modes use the same solver grid, substeps, seeds, and quote-distance shifts. Quick mode changes path counts, not time resolution. Calls for different initial inventories reuse the corresponding seed; the resulting estimates should not be treated as mutually independent samples.

## Dynamics and objective

The intensity used by the original code is

```text
f(d, x) = Lam * exp(-a*d) / sqrt(1 + 3*exp(k*(d-x)))
```

Here `d` is the maker's own quote distance from the reference price and `x` is the best rival quote distance on the same side. The ask price is `S + d_a`; the bid price is `S - d_b`.

Each simulated path contributes the objective

```text
terminal cash + terminal inventory * terminal reference price
- liq * terminal inventory**2
- sum(0.5 * gamma * sigma**2 * inventory**2 * simulation_dt)
```

The baseline theoretical comparison is `q0*S0 + theta[q0](0)`. It includes the initial inventory endowment. Deviation results compare strategies at the same starting inventory.

In A, rivals enter through fixed distributions `Pa` and `Pb`, derived from the maximum and minimum of three independently drawn rival inventories. The same random draw sequence is used for baseline and shifted strategies. Reported deviation uncertainty is calculated from the paired pathwise differences.

In B, the three rivals' initial inventories are drawn independently from the prior, and maker 0's initial inventory is set to `q0`. Makers share the reference-price path. Rates depend on their own inventory-dependent quote and the smallest available rival quote distance. The belief figure retains only the `q0=0` best-ask records; it does not display all initial-inventory cases or the bid-side distribution.

## Numerical methods

The equilibrium ODE is integrated **backward in time using explicit Euler**. This is not the implicit method conventionally called backward Euler. At each grid point, `solve_side()` iterates a best-response map, with each scalar first-order condition solved by bisection.

| Solver setting | Source default |
|---|---:|
| Fixed-point iteration limit | 120 |
| Scalar bisection iterations | 45 |
| Fixed-point stopping tolerance | `1e-9` |
| Scalar search interval | `[-10, 10]` |

Simulation arrivals use independent Bernoulli comparisons with probability `rate * simulation_dt`, allowing at most one execution per side per substep. Quotes are recomputed at each substep from current inventories and the grid-indexed policy. See [numerical limitations](numerical-limitations.md) for consequences of these approximations.

## Separate Bayesian experiment

Running `mm_bayes.py` invokes a different experiment; it is not required to generate the two main simulation figures.

| Setting | Bayesian main routine |
|---|---|
| Inventory bound and rivals | `Q=5`, 3 rivals |
| Solver steps over the full horizon | 50 |
| Observation time / solve endpoint | `T0=0.5` |
| Tracked reference inventory | 0 |
| Observation noise scales | 0.005, 0.02, 0.05, 0.10, 0.30 |
| Observations per noise scale | 2,000 |
| Posterior-belief solves per noise scale | First 80 of those observations |
| Seed | 1 |
| Other comparison | Rival counts 1 through 7 |
| Output files | `oracle_ask.npy`, `bayes_results.json` in the working directory |

The posterior is based on a single noisy observation under a specified prior-equilibrium quote map. Its point-mass oracle cases and posterior-weighted solves have the limited interpretation described in [numerical limitations](numerical-limitations.md).

The report's `Q=10` paper-belief benchmark comparisons, refinements up to 1,600 steps, and other auxiliary claims are separate configurations. The main quick/full command does not automatically perform them.
