"""Run the unchanged reference main routine and retain full-precision evidence.

The hooks observe returned arrays and execution state. They do not change
parameters, random draws, payoffs, or plots. Output directories must be new.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Tee:
    def __init__(self, stream, saved):
        self.stream, self.saved = stream, saved

    def write(self, text):
        self.stream.write(text)
        self.saved.write(text)
        self.saved.flush()
        return len(text)

    def flush(self):
        self.stream.flush()
        self.saved.flush()


def write_csv(path, rows):
    if rows:
        with path.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def distribution_inventory():
    inventory = {}
    for distribution in importlib.metadata.distributions():
        inventory.setdefault(distribution.metadata['Name'], []).append(
            {'version': distribution.version, 'location': str(distribution.locate_file(''))})
    return inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error('Choose an empty or new output directory; recorded evidence is never overwritten.')
    output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR', str(output / '.matplotlib'))
    import numpy as np
    import matplotlib
    import simulate_game as sim

    source_names = ('mm_dynamic.py', 'mm_bayes.py', 'simulate_game.py')
    try:
        source_commit = subprocess.check_output(
            ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True,
            stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        source_commit = None
    summary = {'experiment_A': [], 'deviations': [], 'experiment_B': [], 'beliefs': [], 'observed_simulation': {}}
    baselines = {}
    current = {'label': None}
    original_reference, original_game = sim.simulate_reference, sim.simulate_game
    original_build = sim.build_equilibrium
    captured_eq = {}

    def build():
        result = original_build()
        captured_eq.update(result)
        return result

    def stats(pay):
        return {'mean': float(pay.mean()), 'standard_error': float(pay.std(ddof=1) / np.sqrt(len(pay)))}

    def reference(eq, q0, c, n_paths, seed):
        label = f'A:q0={q0}:c={c}'
        current['label'] = label
        pay, max_rate_dt = original_reference(eq, q0, c, n_paths, seed)
        current['label'] = None
        theory = float(q0 * sim.S0 + eq['theta'][0, q0 + sim.Q])
        if q0 not in baselines:
            baselines[q0] = pay.copy()
            row = {'q0': q0, 'paths': n_paths, 'seed': seed, 'theory': theory, **stats(pay)}
            row['difference'] = row['mean'] - theory
            row['difference_in_standard_errors'] = row['difference'] / row['standard_error']
            row['max_rate_times_dt'] = float(max_rate_dt)
            summary['experiment_A'].append(row)
        else:
            difference = pay - baselines[q0]
            summary['deviations'].append({'q0': q0, 'shift': c, 'paths': n_paths, 'seed': seed,
                                         'mean_difference': float(difference.mean()),
                                         'paired_standard_error': float(difference.std(ddof=1) / np.sqrt(n_paths)),
                                         'max_rate_times_dt': float(max_rate_dt)})
        return pay, max_rate_dt

    def game(eq, q0, n_paths, seed, record_times=(0.0, 0.5, 0.9)):
        label = f'B:q0={q0}'
        current['label'] = label
        pay, record = original_game(eq, q0, n_paths, seed, record_times)
        current['label'] = None
        theory = float(q0 * sim.S0 + eq['theta'][0, q0 + sim.Q])
        row = {'q0': q0, 'paths': n_paths, 'seed': seed, 'theory': theory, **stats(pay)}
        row['difference'] = row['mean'] - theory
        row['difference_in_standard_errors'] = row['difference'] / row['standard_error']
        row['gap_percent_of_theta'] = 100 * row['difference'] / abs(theory - q0 * sim.S0)
        summary['experiment_B'].append(row)
        for index, inventories in sorted(record.items()):
            counts = [int((inventories == q).sum()) for q in range(-sim.Q + 1, sim.Q + 1)]
            retained = len(inventories)
            probabilities = np.array(counts, dtype=float) / retained if retained else np.zeros(2 * sim.Q)
            summary['beliefs'].append({'q0': q0, 'time': index * sim.P.T / sim.P.nsteps,
                                      'initial_paths': n_paths, 'retained_ask_samples': retained,
                                      'excluded_no_ask_samples': n_paths - retained,
                                      'inventories': list(range(-sim.Q + 1, sim.Q + 1)), 'counts': counts,
                                      'probabilities': probabilities.tolist(), 'assumed_probabilities': eq['Pa'].tolist(),
                                      'total_variation_distance': float(0.5 * np.abs(probabilities - eq['Pa']).sum())})
        return pay, record

    # Inspect the unchanged functions' existing state at the pre-penalty line.
    # This adds no random calls and no assignments to the simulation state.
    watched = {}
    for function in (original_reference, original_game):
        lines, start = inspect.getsourcelines(function)
        watched[function.__code__] = next(start + i for i, line in enumerate(lines) if 'pen +=' in line)

    def trace(frame, event, arg):
        target = watched.get(frame.f_code)
        if target is None:
            return None
        if event == 'line' and frame.f_lineno == target:
            values = frame.f_locals
            label = current['label']
            observed = summary['observed_simulation'].setdefault(label, {
                'inventory_min': sim.Q, 'inventory_max': -sim.Q, 'simultaneous_bid_ask_hits': 0,
                'max_rate_times_dt': 0.0, 'maker_substeps': 0,
                'no_rival_ask_maker_substeps': 0, 'no_rival_bid_maker_substeps': 0})
            inventory = values['q']
            observed['inventory_min'] = min(observed['inventory_min'], int(inventory.min()))
            observed['inventory_max'] = max(observed['inventory_max'], int(inventory.max()))
            observed['maker_substeps'] += int(inventory.size)
            observed['simultaneous_bid_ask_hits'] += int(np.count_nonzero(values['hit_a'] & values['hit_b']))
            if frame.f_code is original_game.__code__:
                observed['max_rate_times_dt'] = max(observed['max_rate_times_dt'], float(max(values['ra'].max(), values['rb'].max()) * values['dt']))
                observed['no_rival_ask_maker_substeps'] += int(np.count_nonzero(values['rival_a'] >= values['BIG']))
                observed['no_rival_bid_maker_substeps'] += int(np.count_nonzero(values['rival_b'] >= values['BIG']))
            else:
                observed['max_rate_times_dt'] = float(values['max_rate_dt'])
        elif event == 'return' and frame.f_locals.get('q') is not None:
            observed = summary['observed_simulation'].get(current['label'])
            if observed is not None:
                inventory = frame.f_locals['q']
                observed['inventory_min'] = min(observed['inventory_min'], int(inventory.min()))
                observed['inventory_max'] = max(observed['inventory_max'], int(inventory.max()))
        return trace

    manifest = {'status': 'running', 'started_utc': datetime.now(timezone.utc).isoformat(),
                'invocation': [sys.executable, *sys.argv], 'equivalent_source_command': 'python simulate_game.py' + (' --quick' if args.quick else ''),
                'working_directory': str(output), 'source_commit_at_run': source_commit,
                'source_sha256': {name: digest(ROOT / name) for name in source_names},
                'helper_sha256': digest(__file__), 'python': platform.python_version(),
                'python_executable': sys.executable, 'operating_system': platform.platform(),
                'machine': platform.machine(), 'processor': platform.processor(),
                'numpy': np.__version__, 'matplotlib': matplotlib.__version__,
                'active_module_locations': {'numpy': np.__file__, 'matplotlib': matplotlib.__file__},
                'installed_distributions': distribution_inventory(),
                'mode': 'quick' if args.quick else 'full', 'paths_A': 4000 if args.quick else 40000,
                'paths_B': 2000 if args.quick else 20000, 'parameters': asdict(sim.P),
                'simulation_substeps': sim.SUB, 'simulation_dt': sim.P.T / sim.P.nsteps / sim.SUB,
                'rivals': sim.M_RIVALS, 'prior_scale': sim.PRIOR_SD, 'initial_price': sim.S0,
                'initial_inventories': list(sim.Q0_LIST), 'shifts': list(sim.SHIFTS), 'seed_A': sim.SEED, 'seed_B': sim.SEED + 1,
                'instrumentation': 'Unchanged source main with passive returned-array hooks and line-state observations; no parameter or RNG changes.',
                'observation_notes': ['Experiment A rate maxima are bounds over the entire precomputed inventory/time table, not only visited states.',
                                      'Experiment B rate maxima are over actually visited maker states after quote-availability masks.',
                                      'Each A shift-zero trace aggregates two source calls: initial baseline and repeated zero-shift comparison.',
                                      'Other A shifts and B initial inventories each contain one simulation call.']}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    sim.build_equilibrium, sim.simulate_reference, sim.simulate_game = build, reference, game
    previous_trace, previous_argv, previous_cwd = sys.gettrace(), sys.argv[:], Path.cwd()
    start_time = time.perf_counter()
    exit_code = 0
    try:
        with (output / 'console.log').open('w', encoding='utf-8') as log:
            with contextlib.redirect_stdout(Tee(sys.stdout, log)), contextlib.redirect_stderr(Tee(sys.stderr, log)):
                os.chdir(output)
                sys.argv = [str(ROOT / 'simulate_game.py')] + (['--quick'] if args.quick else [])
                sys.settrace(trace)
                sim.main()
    except BaseException as error:
        manifest['error'] = repr(error)
        exit_code = 1
        raise
    finally:
        sys.settrace(previous_trace)
        sys.argv = previous_argv
        os.chdir(previous_cwd)
        manifest['elapsed_seconds'] = time.perf_counter() - start_time
        manifest['ended_utc'] = datetime.now(timezone.utc).isoformat()
        manifest['exit_code'] = exit_code
        manifest['status'] = 'completed' if exit_code == 0 else 'failed'
        manifest['generated_figure_sha256'] = {name: digest(output / name) for name in ('fig_sim_deviation.png', 'fig_sim_belief.png') if (output / name).exists()}
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        write_csv(output / 'experiment_A.csv', summary['experiment_A'])
        write_csv(output / 'experiment_B.csv', summary['experiment_B'])
        write_csv(output / 'deviations.csv', summary['deviations'])
        belief_rows = []
        for row in summary['beliefs']:
            for q, count, actual, assumed in zip(row['inventories'], row['counts'], row['probabilities'], row['assumed_probabilities']):
                belief_rows.append({key: value for key, value in row.items() if key not in ('inventories', 'counts', 'probabilities', 'assumed_probabilities')} | {'inventory': q, 'count': count, 'probability': actual, 'assumed_probability': assumed})
        write_csv(output / 'beliefs.csv', belief_rows)
    print(f'Retained evidence in {output}')


if __name__ == '__main__':
    main()
