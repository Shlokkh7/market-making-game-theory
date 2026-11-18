"""Diagnostics for the default equilibrium; does not modify reference source.

Checks algebraic/numerical residuals on the supplied grid. These checks do not
establish time-grid convergence or optimality over all possible deviations.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def evaluate():
    import numpy as np
    import matplotlib
    import mm_dynamic as dynamic
    import simulate_game as sim

    calls = []
    active = {'call': None}
    original_side, original_G = dynamic.solve_side, dynamic._G

    def counted_G(*args, **kwargs):
        if active['call'] is not None:
            active['call']['first_order_evaluations'] += 1
        return original_G(*args, **kwargs)

    def observed_side(*args, **kwargs):
        info = {'first_order_evaluations': 0, 'outer_limit': kwargs.get('outer', 120),
                'bisections_per_iteration': kwargs.get('bis', 45)}
        active['call'] = info
        result = original_side(*args, **kwargs)
        info['iterations'] = info['first_order_evaluations'] // info['bisections_per_iteration']
        info['iteration_limit_reached'] = info['iterations'] >= info['outer_limit']
        info['exhausted_without_tolerance'] = info['iteration_limit_reached'] and info['final_update_error'] >= info['tolerance']
        calls.append(info)
        active['call'] = None
        return result

    def profile(frame, event, arg):
        if event == 'return' and frame.f_code is original_side.__code__ and active['call'] is not None:
            active['call']['final_update_error'] = float(frame.f_locals['err'])
            active['call']['tolerance'] = float(frame.f_locals['tol'])

    started = time.perf_counter()
    previous_profile = sys.getprofile()
    try:
        dynamic.solve_side, dynamic._G = observed_side, counted_G
        sys.setprofile(profile)
        eq = sim.build_equilibrium()
    finally:
        sys.setprofile(previous_profile)
        dynamic.solve_side, dynamic._G = original_side, original_G

    residuals = []
    for n, theta in enumerate(eq['theta']):
        for side, spread, delta, belief in (
                ('ask', eq['wa'][n], theta[:-1] - theta[1:], eq['Pa']),
                ('bid', eq['wb'][n], theta[1:] - theta[:-1], eq['Pb'])):
            lower, upper = np.full_like(spread, -10.0), np.full_like(spread, 10.0)
            gl, gu = original_G(lower, spread, delta, belief, sim.P), original_G(upper, spread, delta, belief, sim.P)
            one_update = original_side(delta, belief, spread, sim.P, outer=1)
            residuals.append({'time': n * sim.P.T / sim.P.nsteps, 'side': side,
                              'max_abs_first_order_residual': float(np.max(np.abs(original_G(spread, spread, delta, belief, sim.P)))),
                              'max_abs_fixed_point_residual': float(np.max(np.abs(one_update - spread))),
                              'brackets_all_roots': bool(np.all(gl > 0) and np.all(gu < 0)),
                              'nearest_root_interval_endpoint': float(min((spread + 10).min(), (10 - spread).min())),
                              'finite': bool(np.all(np.isfinite(spread)) and np.all(np.isfinite(gl)) and np.all(np.isfinite(gu)))})
    max_foc = max(row['max_abs_first_order_residual'] for row in residuals)
    max_fixed = max(row['max_abs_fixed_point_residual'] for row in residuals)
    rate_rows = []
    for shift in sim.SHIFTS:
        _, _, ga, gb = sim.spread_and_rate_tables(eq, shift)
        rate_rows.append({'shift': shift, 'max_rate_times_dt': float(max(ga.max(), gb.max()) * sim.P.T / sim.P.nsteps / sim.SUB),
                          'nonnegative_rates': bool(np.all(ga >= 0) and np.all(gb >= 0)),
                          'ask_disabled_at_lower_bound': bool(np.all(ga[:, 0] == 0)),
                          'bid_disabled_at_upper_bound': bool(np.all(gb[:, -1] == 0))})
    q = np.arange(-sim.Q, sim.Q + 1)
    terminal_error = float(np.max(np.abs(eq['theta'][-1] + sim.P.liq * q ** 2)))
    all_finite = all(np.all(np.isfinite(value)) for value in eq.values())
    normalized = all(abs(float(eq[key].sum()) - 1) < 1e-12 and np.all(eq[key] >= 0) for key in ('prior', 'Pa', 'Pb'))
    monotone_ask = bool(np.all(np.diff(eq['wa'], axis=1) <= 1e-9))
    monotone_bid = bool(np.all(np.diff(eq['wb'], axis=1) >= -1e-9))
    symmetry = {'belief_max_abs_error': float(np.max(np.abs(eq['Pa'] - eq['Pb'][::-1]))),
                'quote_max_abs_error': float(np.max(np.abs(eq['wa'] - eq['wb'][:, ::-1])))}
    checks = {'finite_output': bool(all_finite), 'probabilities_normalized': bool(normalized),
              'terminal_condition': terminal_error < 1e-12,
              'all_roots_bracketed': all(row['brackets_all_roots'] for row in residuals),
              'first_order_residual_below_1e_minus_6': max_foc < 1e-6,
              'fixed_point_residual_below_1e_minus_8': max_fixed < 1e-8,
              'no_iteration_exhaustion': not any(row['exhausted_without_tolerance'] for row in calls),
              'ask_quotes_nonincreasing_in_inventory': monotone_ask,
              'bid_quotes_nondecreasing_in_inventory': monotone_bid,
              'symmetry': symmetry['belief_max_abs_error'] < 1e-10 and symmetry['quote_max_abs_error'] < 1e-8,
              'all_A_rate_times_dt_below_one': all(row['max_rate_times_dt'] < 1 for row in rate_rows),
              'inventory_boundary_rates': all(row['ask_disabled_at_lower_bound'] and row['bid_disabled_at_upper_bound'] for row in rate_rows)}
    return {'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks,
            'created_utc': datetime.now(timezone.utc).isoformat(), 'elapsed_seconds': time.perf_counter() - started,
            'python': platform.python_version(), 'operating_system': platform.platform(), 'numpy': np.__version__, 'matplotlib': matplotlib.__version__,
            'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ('mm_dynamic.py', 'mm_bayes.py', 'simulate_game.py')},
            'solver_calls': len(calls), 'iteration_limit_reached_count': sum(row['iteration_limit_reached'] for row in calls),
            'iteration_exhaustion_count': sum(row['exhausted_without_tolerance'] for row in calls),
            'maximum_fixed_point_iterations': max(row['iterations'] for row in calls),
            'max_abs_first_order_residual': max_foc, 'max_abs_fixed_point_residual': max_fixed,
            'terminal_condition_max_abs_error': terminal_error, 'symmetry': symmetry,
            'initial_theta_q0_zero': float(eq['theta'][0, sim.Q]),
            'rate_diagnostics_A': rate_rows, 'grid_residuals': residuals,
            'iteration_observations': calls,
            'limits': ['Default 100-step solver configuration only; no time-grid refinement is established.',
                       'Residual checks assess the implemented equations; they do not prove global game-theoretic optimality.',
                       'rate*dt < 1 avoids probability saturation but does not establish a desired discretization accuracy.',
                       'Experiment B rates and actual inventory bounds are observed separately in run_experiments.py.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'results' / 'diagnostics.json')
    args = parser.parse_args()
    result = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key not in ('grid_residuals', 'iteration_observations', 'source_sha256')}, indent=2))
    raise SystemExit(0 if result['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
