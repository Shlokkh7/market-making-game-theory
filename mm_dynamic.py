"""
mm_dynamic.py
=============
Numerical solution of the dynamic Nash equilibrium of Luo & Zheng (2021),
"Dynamic Equilibrium of Market Making with Price Competition".

What is solved
--------------
Inventory q in {-Q,...,Q}. Value function  V = x + q*S + theta_q(t).
theta solves the coupled Hamilton-Jacobi ODE system (paper eq. 3.5):

  theta_q'(t) = 0.5*gamma*sigma^2*q^2
                - sup_d eta^a(theta,d,pi^a,q) * I^a(q)
                - sup_d eta^b(theta,d,pi^b,q) * I^b(q),
  theta_q(T)  = -l(|q|),   l(q) = liq * q^2

  eta^a(mu,d,xi,q) = sum_j Pa_j f(d, xi_j) (d + mu_{q-1} - mu_q)
  eta^b(mu,d,xi,q) = sum_j Pb_j f(d, xi_j) (d + mu_{q+1} - mu_q)

and pi^a, pi^b are the equilibrium spreads: every market maker with
inventory q plays the best response to everybody else playing pi.
Pa_j = probability that the MOST COMPETITIVE rival ask comes from a market
maker with inventory j (Pb_j analogously for bids). These encode the
incomplete information about rivals' inventories.

Intensity (paper eq. 2.2, as we read the garbled PDF text):
  f(d, x) = Lam * exp(-a d) / sqrt(1 + 3 exp(k (d - x)))
At d == x this is Lam*exp(-a d)/2, which is why the benchmark uses 0.5*Lam.

Benchmark (Gueant 2017, no competition): f~(d) = 0.5*Lam*exp(-a d).
There the sup is closed form:  d* = 1/a - (mu_{q-1}-mu_q).

Numerical method
----------------
Backward explicit Euler in time. At each time step the "generalized Isaacs"
fixed point  w = T(w)  (paper Step 1, Theorem 5.2) is found by iterating
the best-response map T, where each coordinate of T is the root of a
scalar first-order condition found by vectorised bisection (the root is
unique by the paper's Lemma 5.1).
"""
from dataclasses import dataclass
import numpy as np


@dataclass
class Params:
    Lam: float = 60.0
    a: float = 2.0
    k: float = 2.0
    gamma: float = 1.0
    sigma: float = 0.01
    T: float = 1.0
    nsteps: int = 100
    Q: int = 10
    liq: float = 0.1      # terminal liquidity penalty l(q) = liq * q^2


# ----------------------------------------------------------------------
# intensity function and the ratio h = -f_1 / f
# ----------------------------------------------------------------------
def f(d, x, p):
    return p.Lam * np.exp(-p.a * d) / np.sqrt(1.0 + 3.0 * np.exp(p.k * (d - x)))


def h(d, x, p):
    """-f_1/f. From f = Lam e^{-a d}(1+3E)^(-1/2), E=e^{k(d-x)}:
       d/dd ln f = -a - 1.5 k E/(1+3E)."""
    E = np.exp(p.k * (d - x))
    return p.a + 1.5 * p.k * E / (1.0 + 3.0 * E)


# ----------------------------------------------------------------------
# equilibrium of one side (ask or bid) at a fixed time, given mu=theta(t)
# ----------------------------------------------------------------------
def _G(d, w, Delta, P, p):
    """First-order condition of eta wrt own spread d (vector over own state i).
       d eta_i/d d  =  sum_j P_j f(d_i,w_j) [ 1 - h(d_i,w_j)(d_i + Delta_i) ]"""
    D = d[:, None]
    X = w[None, :]
    return np.sum(P[None, :] * f(D, X, p) * (1.0 - h(D, X, p) * (D + Delta[:, None])), axis=1)


def solve_side(Delta, P, w0, p, outer=120, bis=45, tol=1e-9):
    """Fixed point w = T(w): w_i = argmax_d eta(mu, d, w, i)."""
    w = w0.copy()
    n = len(w)
    for _ in range(outer):
        lo = np.full(n, -10.0)
        hi = np.full(n, 10.0)
        for _ in range(bis):
            mid = 0.5 * (lo + hi)
            pos = _G(mid, w, Delta, P, p) > 0.0
            lo = np.where(pos, mid, lo)
            hi = np.where(pos, hi, mid)
        w_new = 0.5 * (lo + hi)
        err = np.max(np.abs(w_new - w))
        w = w_new
        if err < tol:
            break
    return w


def eta(w, Delta, P, p):
    """Optimised eta at the equilibrium spreads w."""
    return np.sum(P[None, :] * f(w[:, None], w[None, :], p), axis=1) * (w + Delta)


# ----------------------------------------------------------------------
# backward-in-time solution of the full ODE system
# ----------------------------------------------------------------------
def solve_dynamic(Pa, Pb, p, t_stop=0.0, model="competition"):
    """
    Returns dict with arrays (time runs from T down to t_stop):
      t[s], theta[s, q], wa[s, i] (ask spreads, q=-Q+1..Q), wb[s, i] (bid, q=-Q..Q-1)
    model = "competition"  -> paper's Nash equilibrium
    model = "benchmark"    -> Gueant (2017), no price competition
    """
    Q = p.Q
    q = np.arange(-Q, Q + 1)
    dt = p.T / p.nsteps
    theta = -p.liq * q.astype(float) ** 2
    n_back = int(round((p.T - t_stop) / dt))
    wa = np.full(2 * Q, 0.3)
    wb = np.full(2 * Q, 0.3)
    out = {"t": [], "theta": [], "wa": [], "wb": []}
    for s in range(n_back + 1):
        Da = theta[:-1] - theta[1:]        # mu_{q-1}-mu_q, q=-Q+1..Q
        Db = theta[1:] - theta[:-1]        # mu_{q+1}-mu_q, q=-Q..Q-1
        if model == "benchmark":
            wa = 1.0 / p.a - Da
            wb = 1.0 / p.a - Db
            ea = 0.5 * p.Lam * np.exp(-p.a * wa) / p.a
            eb = 0.5 * p.Lam * np.exp(-p.a * wb) / p.a
        else:
            wa = solve_side(Da, Pa, wa, p)
            wb = solve_side(Db, Pb, wb, p)
            ea = eta(wa, Da, Pa, p)
            eb = eta(wb, Db, Pb, p)
        out["t"].append(p.T - s * dt)
        out["theta"].append(theta.copy())
        out["wa"].append(wa.copy())
        out["wb"].append(wb.copy())
        if s < n_back:
            dtheta = 0.5 * p.gamma * p.sigma ** 2 * q.astype(float) ** 2
            dtheta[1:] -= ea
            dtheta[:-1] -= eb
            theta = theta - dt * dtheta
    for key in out:
        out[key] = np.array(out[key])
    out["q"] = q
    return out


# ----------------------------------------------------------------------
# beliefs P^a, P^b used in the paper's numerical section (p.564)
# ----------------------------------------------------------------------
def paper_beliefs(Q=10):
    """Pa over q=-Q+1..Q ; Pb over q=-Q..Q-1 (index order as in solver)."""
    qa = np.arange(-Q + 1, Q + 1)
    qb = np.arange(-Q, Q)
    # paper: Pa_0=.2, Pa_1=.4, Pa_2=.3, others 1/170 (Q=10)
    Pa = np.full(2 * Q, 1.0 / 170.0)
    Pb = np.full(2 * Q, 1.0 / 170.0)
    for val, qq in zip((0.2, 0.4, 0.3), (0, 1, 2)):
        Pa[qa == qq] = val
    for val, qq in zip((0.2, 0.4, 0.3), (0, -1, -2)):
        Pb[qb == qq] = val
    return Pa, Pb
