"""
mm_bayes.py
===========
Bayesian extension of the Luo & Zheng (2021) market making equilibrium.

Idea
----
In the paper, Pa_j / Pb_j (the probability that the best rival ask / bid
comes from a market maker with inventory j) are GIVEN and fixed. Here they
are DERIVED and UPDATED:

 1. Prior: each of the M rivals has an inventory drawn iid from a prior p0(q).
 2. Because the equilibrium ask spread is decreasing in inventory and the bid
    spread increasing, the best ask belongs to the rival with the MAX
    inventory and the best bid to the rival with the MIN inventory
    (this is exactly the logic of the paper's Example 2.2).
    So (Pa, Pb) are the marginals of the joint law of (max, min) of M iid draws.
 3. Observation: at time t0 we see the best ask / bid with noise,
        s_a = pi^a_{qmax}(t0) + eps_a ,  s_b = pi^b_{qmin}(t0) + eps_b ,
    eps ~ N(0, sig^2). The rival strategies pi are the prior-equilibrium ones
    (rational expectations / common knowledge of the strategy map).
 4. Bayes:  p(qmax, qmin | s_a, s_b)  ∝  p(qmax, qmin) * L(s_a|qmax) * L(s_b|qmin).
 5. Equilibrium distribution. Two objects are computed for every observation:
    (A) the posterior-weighted distribution over the COMPLETE-INFORMATION
        equilibria "oracle[qmax,qmin]" (one Nash equilibrium per possible case);
    (B) the Bayesian-belief equilibrium: the paper's equilibrium solved with
        the posterior marginals as (Pa, Pb).  B != mean of A in general,
        because best-responding to an average belief is not the same as
        averaging best responses (Jensen).
"""
import json, os, sys, time
import numpy as np
from mm_dynamic import Params, solve_dynamic, f

Q = 5
P = Params(Q=Q, nsteps=50)
T0 = 0.5          # observation time; equilibrium is solved on [T0, T]
M_RIVALS = 3
PRIOR_SD = 2.0
Q_REF = 0         # inventory of the reference market maker whose spread we track
IA_REF = Q_REF + Q - 1      # index of q=Q_REF in the ask array (q=-Q+1..Q)
IB_REF = Q_REF + Q          # index of q=Q_REF in the bid array (q=-Q..Q-1)
NS = 2 * Q + 1              # number of inventory states, index m <-> q=m-Q


def discretized_normal(sd, Q=Q):
    q = np.arange(-Q, Q + 1)
    w = np.exp(-0.5 * (q / sd) ** 2)
    return w / w.sum()


def joint_max_min(prior, M):
    """J[j,i] = P(max index = j, min index = i), i<=j, for M iid draws,
    restricted to cases where an ask (max>=1) and a bid (min<=NS-2) exist."""
    C = np.concatenate([[0.0], np.cumsum(prior)])
    def G(i, j):
        return 0.0 if i > j else (C[j + 1] - C[i]) ** M
    J = np.zeros((NS, NS))
    for j in range(NS):
        for i in range(j + 1):
            J[j, i] = G(i, j) - G(i + 1, j) - G(i, j - 1) + G(i + 1, j - 1)
    J[0, :] = 0.0            # max = -Q: nobody quotes an ask
    J[:, NS - 1] = 0.0       # min = +Q: nobody quotes a bid
    return J / J.sum()


def marginals(J):
    Pa = J.sum(axis=1)[1:]        # j = 1..2Q   -> q=-Q+1..Q
    Pb = J.sum(axis=0)[:-1]       # i = 0..2Q-1 -> q=-Q..Q-1
    return Pa / Pa.sum(), Pb / Pb.sum()


def equilibrium(Pa, Pb):
    r = solve_dynamic(Pa, Pb, P, t_stop=T0)
    return r["wa"][-1], r["wb"][-1]       # strategies at t = T0


def oracle_table():
    """Complete-information equilibrium for every case (qmax=j, qmin=i)."""
    ask = np.full((NS, NS), np.nan); bid = np.full((NS, NS), np.nan)
    for j in range(1, NS):
        for i in range(0, min(j, NS - 2) + 1):
            Pa = np.zeros(2 * Q); Pa[j - 1] = 1.0
            Pb = np.zeros(2 * Q); Pb[i] = 1.0
            wa, wb = equilibrium(Pa, Pb)
            ask[j, i] = wa[IA_REF]; bid[j, i] = wb[IB_REF]
    return ask, bid


def posterior(J, wa0, wb0, sa, sb, sig):
    """Joint posterior over (qmax index j, qmin index i)."""
    la = -0.5 * ((sa - wa0) / sig) ** 2          # length 2Q, index j-1
    lb = -0.5 * ((sb - wb0) / sig) ** 2          # length 2Q, index i
    L = np.full((NS, NS), -np.inf)
    L[1:, :-1] = la[:, None] + lb[None, :]
    with np.errstate(divide="ignore"):
        lp = np.log(J) + L
    lp -= np.max(lp)
    post = np.exp(lp)
    return post / post.sum()


def simulate_true(rng, prior, M):
    while True:
        qs = rng.choice(NS, size=M, p=prior)
        j, i = qs.max(), qs.min()
        if j >= 1 and i <= NS - 2:
            return j, i


# ----------------------------------------------------------------------
def main(n_A=2000, n_B=80, sigmas=(0.005, 0.02, 0.05, 0.1, 0.3), seed=1):
    rng = np.random.default_rng(seed)
    prior = discretized_normal(PRIOR_SD)
    J = joint_max_min(prior, M_RIVALS)
    Pa0, Pb0 = marginals(J)
    wa0, wb0 = equilibrium(Pa0, Pb0)             # prior equilibrium (rival strategy map)
    prior_spread = wa0[IA_REF]
    print("prior-equilibrium ask spread (q_ref=0, t=0.5): %.4f" % prior_spread)

    if os.path.exists("oracle_ask.npy"):
        ask_or = np.load("oracle_ask.npy")
    else:
        print("computing complete-information equilibria for every case ...", flush=True)
        ask_or, bid_or = oracle_table()
        np.save("oracle_ask.npy", ask_or)

    res = {"prior_spread": prior_spread, "sigmas": list(sigmas), "rows": []}

    # ---- effect of the NUMBER of rivals (prior beliefs only) ----
    byM = []
    for M in range(1, 8):
        Jm = joint_max_min(prior, M); Pam, Pbm = marginals(Jm)
        wam, _ = equilibrium(Pam, Pbm)
        byM.append((M, wam[IA_REF], Pam.tolist()))
        print(f"  M={M} rivals: ask spread {wam[IA_REF]:.4f}", flush=True)
    res["byM"] = byM

    # ---- Monte Carlo over observations ----
    for sig in sigmas:
        errs_prior, errs_A, sd_A, errs_B, errs_B_vs_A = [], [], [], [], []
        for n in range(n_A):
            j, i = simulate_true(rng, prior, M_RIVALS)
            sa = wa0[j - 1] + sig * rng.standard_normal()
            sb = wb0[i] + sig * rng.standard_normal()
            post = posterior(J, wa0, wb0, sa, sb, sig)
            vals = ask_or; m = np.isfinite(vals) & (post > 0)
            meanA = np.sum(post[m] * vals[m])
            sdA = np.sqrt(np.sum(post[m] * (vals[m] - meanA) ** 2))
            truth = ask_or[j, i]
            errs_prior.append(prior_spread - truth)
            errs_A.append(meanA - truth); sd_A.append(sdA)
            if n < n_B:
                Pa_p, Pb_p = marginals(post)
                t_s = time.time()
                wa_b, _ = equilibrium(Pa_p, Pb_p)
                if time.time() - t_s > 5:
                    print("   slow solve (%.1fs) at sig=%.3f n=%d" % (time.time() - t_s, sig, n), flush=True)
                errs_B.append(wa_b[IA_REF] - truth)
                errs_B_vs_A.append(wa_b[IA_REF] - meanA)
        row = dict(sig=sig,
                   rmse_prior=float(np.sqrt(np.mean(np.square(errs_prior)))),
                   rmse_A=float(np.sqrt(np.mean(np.square(errs_A)))),
                   sd_A=float(np.mean(sd_A)),
                   rmse_B=float(np.sqrt(np.mean(np.square(errs_B)))),
                   rmse_A_sub=float(np.sqrt(np.mean(np.square(errs_A[:n_B])))),
                   rmse_prior_sub=float(np.sqrt(np.mean(np.square(errs_prior[:n_B])))),
                   rms_B_minus_A=float(np.sqrt(np.mean(np.square(errs_B_vs_A)))),
                   gap_B_minus_A=float(np.mean(errs_B_vs_A)))
        res["rows"].append(row)
        json.dump(res, open("bayes_results.json", "w"), indent=1)
        print("sig=%.3f | all %d draws: prior-eq %.4f, A %.4f | same %d draws: prior-eq %.4f, A %.4f, B %.4f | rms(B-A) %.4f | mean posterior sd %.4f"
              % (sig, n_A, row["rmse_prior"], row["rmse_A"], n_B, row["rmse_prior_sub"], row["rmse_A_sub"], row["rmse_B"], row["rms_B_minus_A"], row["sd_A"]), flush=True)
    json.dump(res, open("bayes_results.json", "w"), indent=1)


if __name__ == "__main__":
    main()
