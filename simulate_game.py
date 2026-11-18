"""
simulate_game.py
================
Monte Carlo simulation of the market making game, used to VALIDATE the
numerical equilibrium of Luo & Zheng (2021) computed in mm_dynamic.py.

Two experiments
---------------
A. Reference-maker test  (checks the theta equation AND the Nash property)
   One maker plays the equilibrium; rivals enter only through the belief
   P^a, P^b (exactly as in the paper's HJB derivation).
   A1. Mean simulated payoff  should equal  q0*S0 + theta_{q0}(0).
   A2. Deviation test: if she shifts all her spreads by a constant c
       while rivals keep playing the equilibrium, her mean payoff should
       be highest at c = 0 (that is what "best response" means).
       Paired comparisons use common random numbers (same random draws).

B. Explicit multi-maker game  (checks the paper's fixed-belief assumption)
   M+1 makers each hold an inventory and quote pi(q, t). Maker i's order
   rate is f(own spread, lowest rival spread). The paper assumes the
   probability P^a that the best rival has inventory j is CONSTANT in time.
   Here we measure what it really is, and how far the payoff of maker 0
   is from the theoretical value as a result.

Usage
-----
    python simulate_game.py            # full run  (a few minutes)
    python simulate_game.py --quick    # small run (about 1 minute)
Requires mm_dynamic.py and mm_bayes.py in the same folder.
"""
import argparse
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mm_dynamic import Params, solve_dynamic, f
from mm_bayes import discretized_normal, joint_max_min, marginals

# ----------------------------------------------------------------------
# settings
# ----------------------------------------------------------------------
Q = 5
M_RIVALS = 3                 # number of rivals
PRIOR_SD = 2.0               # prior std of rival inventory (same as Bayes part)
P = Params(Q=Q, nsteps=100)
S0 = 20.0                    # initial reference price
SUB = 10                     # simulation substeps per grid step
Q0_LIST = (-3, 0, 3)         # initial inventories of the reference maker
SHIFTS = (-0.2, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2)   # deviation sizes c
SEED = 7


def build_equilibrium():
    """Equilibrium strategies in FORWARD time (index n <-> t = n*dt)."""
    prior = discretized_normal(PRIOR_SD, Q)
    J = joint_max_min(prior, M_RIVALS)
    Pa, Pb = marginals(J)
    res = solve_dynamic(Pa, Pb, P, t_stop=0.0)
    eq = dict(
        prior=prior, Pa=Pa, Pb=Pb,
        theta=res["theta"][::-1],     # (nsteps+1, 2Q+1), index m = q+Q
        wa=res["wa"][::-1],           # (nsteps+1, 2Q),  index i = q+Q-1
        wb=res["wb"][::-1],           # (nsteps+1, 2Q),  index i = q+Q
    )
    return eq


# ----------------------------------------------------------------------
# Experiment A: reference maker, rivals only through the belief
# ----------------------------------------------------------------------
def spread_and_rate_tables(eq, c):
    """Spread tables DA, DB and expected arrival-rate tables GA, GB, indexed
    [n, m] with m = q + Q. Unavailable quotes (q=-Q ask, q=+Q bid) get
    spread 0 and rate 0."""
    n = P.nsteps
    DA = np.zeros((n, 2 * Q + 1)); DB = np.zeros((n, 2 * Q + 1))
    GA = np.zeros((n, 2 * Q + 1)); GB = np.zeros((n, 2 * Q + 1))
    wa, wb = eq["wa"][:n], eq["wb"][:n]
    DA[:, 1:] = wa + c
    DB[:, :-1] = wb + c
    # expected rate = sum_j P_j f(my spread, rival spread_j)
    GA[:, 1:] = np.sum(eq["Pa"][None, None, :] * f(DA[:, 1:, None], wa[:, None, :], P), axis=2)
    GB[:, :-1] = np.sum(eq["Pb"][None, None, :] * f(DB[:, :-1, None], wb[:, None, :], P), axis=2)
    return DA, DB, GA, GB


def simulate_reference(eq, q0, c, n_paths, seed):
    """Payoff of every path for one maker with initial inventory q0 whose
    spreads are the equilibrium spreads shifted by c."""
    rng = np.random.default_rng(seed)          # same seed => common random numbers
    DA, DB, GA, GB = spread_and_rate_tables(eq, c)
    dt = P.T / P.nsteps / SUB
    q = np.full(n_paths, q0, dtype=int)
    X = np.zeros(n_paths)
    S = np.full(n_paths, S0)
    pen = np.zeros(n_paths)
    max_rate_dt = max(GA.max(), GB.max()) * dt
    for n in range(P.nsteps):
        for _ in range(SUB):
            m = q + Q
            ua = rng.random(n_paths); ub = rng.random(n_paths); z = rng.standard_normal(n_paths)
            hit_a = ua < GA[n, m] * dt
            hit_b = ub < GB[n, m] * dt
            pen += 0.5 * P.gamma * P.sigma ** 2 * q.astype(float) ** 2 * dt
            X += hit_a * (S + DA[n, m]) - hit_b * (S - DB[n, m])
            q = q + hit_b.astype(int) - hit_a.astype(int)
            S = S + P.sigma * np.sqrt(dt) * z
    payoff = X + q * S - P.liq * q.astype(float) ** 2 - pen
    return payoff, max_rate_dt


def experiment_A(eq, n_paths):
    print("\n=== Experiment A: reference maker (rivals enter through the belief) ===")
    out = {}
    for q0 in Q0_LIST:
        theory = q0 * S0 + eq["theta"][0, q0 + Q]
        base, mr = simulate_reference(eq, q0, 0.0, n_paths, SEED)
        se = base.std(ddof=1) / np.sqrt(n_paths)
        print(f"q0={q0:+d}: simulated {base.mean():.3f} +/- {se:.3f}   theory {theory:.3f}   "
              f"difference {base.mean() - theory:+.3f} ({(base.mean() - theory) / se:+.1f} s.e.)   "
              f"[max rate*dt = {mr:.2f}]")
        diffs = []
        for c in SHIFTS:
            pay, _ = simulate_reference(eq, q0, c, n_paths, SEED)
            d = pay - base
            diffs.append((c, d.mean(), d.std(ddof=1) / np.sqrt(n_paths)))
        out[q0] = diffs
        row = "   deviation c -> payoff change vs c=0:  " + "   ".join(
            f"{c:+.2f}: {m:+.3f}({s:.3f})" for c, m, s in diffs)
        print(row)
    return out


# ----------------------------------------------------------------------
# Experiment B: explicit multi-maker game
# ----------------------------------------------------------------------
def simulate_game(eq, q0, n_paths, seed, record_times=(0.0, 0.5, 0.9)):
    """K = M+1 makers quote pi(q, t) and are hit at rate f(own spread, lowest
    rival spread). Quotes are recomputed after every event (every substep)."""
    rng = np.random.default_rng(seed)
    K = M_RIVALS + 1
    dt = P.T / P.nsteps / SUB
    # maker 0 is the reference maker; the others draw inventories from the prior
    q = rng.choice(2 * Q + 1, size=(n_paths, K), p=eq["prior"]) - Q
    q[:, 0] = q0
    X = np.zeros((n_paths, K)); S = np.full(n_paths, S0)
    pen = np.zeros((n_paths, K))
    wa, wb = eq["wa"], eq["wb"]
    BIG = 1e6
    idx = np.arange(n_paths)
    record = {int(round(t / (P.T / P.nsteps))): [] for t in record_times}
    for n in range(P.nsteps):
        for sub in range(SUB):
            quote_a = q >= -Q + 1
            quote_b = q <= Q - 1
            da = np.where(quote_a, wa[n][np.clip(q + Q - 1, 0, 2 * Q - 1)], BIG)
            db = np.where(quote_b, wb[n][np.clip(q + Q, 0, 2 * Q - 1)], BIG)
            if sub == 0 and n in record:             # inventory of the best-ask rival
                best = np.argmin(da[:, 1:], axis=1) + 1
                ok = da[idx, best] < BIG
                record[n] = q[idx, best][ok]
            rival_a = np.empty_like(da); rival_b = np.empty_like(db)
            for i in range(K):
                others = [j for j in range(K) if j != i]
                rival_a[:, i] = da[:, others].min(axis=1)
                rival_b[:, i] = db[:, others].min(axis=1)
            x_a = np.where(rival_a >= BIG, 10.0, rival_a)      # nobody else quotes: no competition
            x_b = np.where(rival_b >= BIG, 10.0, rival_b)
            da0 = np.where(quote_a, da, 0.0); db0 = np.where(quote_b, db, 0.0)
            ra = np.where(quote_a, f(da0, x_a, P), 0.0)
            rb = np.where(quote_b, f(db0, x_b, P), 0.0)
            ua = rng.random((n_paths, K)); ub = rng.random((n_paths, K)); z = rng.standard_normal(n_paths)
            hit_a = ua < ra * dt
            hit_b = ub < rb * dt
            pen += 0.5 * P.gamma * P.sigma ** 2 * q.astype(float) ** 2 * dt
            X += hit_a * (S[:, None] + da0) - hit_b * (S[:, None] - db0)
            q = q + hit_b.astype(int) - hit_a.astype(int)
            S = S + P.sigma * np.sqrt(dt) * z
    payoff = X[:, 0] + q[:, 0] * S - P.liq * q[:, 0].astype(float) ** 2 - pen[:, 0]
    return payoff, record


def experiment_B(eq, n_paths):
    print("\n=== Experiment B: explicit game with %d makers ===" % (M_RIVALS + 1))
    results = {}
    for q0 in Q0_LIST:
        theory = q0 * S0 + eq["theta"][0, q0 + Q]
        pay, rec = simulate_game(eq, q0, n_paths, SEED + 1)
        se = pay.std(ddof=1) / np.sqrt(n_paths)
        print(f"q0={q0:+d}: simulated {pay.mean():.3f} +/- {se:.3f}   theory {theory:.3f}   "
              f"gap {pay.mean() - theory:+.3f} ({100 * (pay.mean() - theory) / abs(theory - q0 * S0):+.1f}% of theta)")
        if q0 == 0:
            results = rec
    return results


# ----------------------------------------------------------------------
def make_figures(devA, rec, eq):
    # deviation figure
    fig, ax = plt.subplots(figsize=(7, 4.4))
    for q0, diffs in devA.items():
        c = [d[0] for d in diffs]; m = [d[1] for d in diffs]; s = [d[2] for d in diffs]
        ax.errorbar(c, m, yerr=[2 * x for x in s], marker="o", capsize=3, label=f"q0 = {q0:+d}")
    ax.axhline(0, color="k", lw=0.8); ax.axvline(0, color="gray", ls=":")
    ax.set(title="Deviation test: payoff change when shifting all spreads by c",
           xlabel="shift c (c = 0 is the equilibrium)", ylabel="mean payoff change (bars: 2 s.e.)")
    ax.legend(); fig.tight_layout(); fig.savefig("fig_sim_deviation.png", dpi=150); plt.close(fig)

    # belief figure
    qa = np.arange(-Q + 1, Q + 1)
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    ax.plot(qa, eq["Pa"], "k--o", lw=2, label="assumed $P^a$ (constant in time)")
    for n, inv in sorted(rec.items()):
        if len(inv) == 0:
            continue
        real = np.array([(inv == j).mean() for j in qa])
        ax.plot(qa, real, "-o", label=f"realised, t = {n * P.T / P.nsteps:.1f}")
        print(f"   total-variation distance, assumed vs realised at t={n * P.T / P.nsteps:.1f}: "
              f"{0.5 * np.abs(real - eq['Pa']).sum():.3f}")
    ax.set(title="Inventory of the best-ask rival: assumption vs simulation",
           xlabel="inventory j", ylabel="probability"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig("fig_sim_belief.png", dpi=150); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="small run for a fast check")
    args = ap.parse_args()
    nA, nB = (4000, 2000) if args.quick else (40000, 20000)
    t0 = time.time()
    eq = build_equilibrium()
    print("equilibrium solved in %.1fs; simulating with %d / %d paths" % (time.time() - t0, nA, nB))
    devA = experiment_A(eq, nA)
    rec = experiment_B(eq, nB)
    make_figures(devA, rec, eq)
    print("\nsaved fig_sim_deviation.png and fig_sim_belief.png   (total %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
