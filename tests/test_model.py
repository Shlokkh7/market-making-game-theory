"""Small mathematical and preservation checks using only the direct dependencies."""
import hashlib
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import mm_dynamic as dynamic
import mm_bayes as bayes


class ModelChecks(unittest.TestCase):
    def test_reference_source_bytes_preserved(self):
        expected = {
            'mm_dynamic.py': '5d3cbefe9870207d7b4fe1b18fa1a225967b23aadb6f328ac96bd52e64a33087',
            'mm_bayes.py': '4ac175f71ced092dc6db6f4720b7592ed504cfed562247232fd36f555ad4e293',
            'simulate_game.py': '182665d3d6818c834995c7b47e2307508734c318e059c4f8ca7c55d8400969da'}
        for name, value in expected.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), value)

    def test_single_rival_extremes_agree(self):
        # With one rival, maximum equals minimum, so all probability is diagonal.
        prior = bayes.discretized_normal(2.0)
        joint = bayes.joint_max_min(prior, 1)
        np.testing.assert_allclose(joint, np.diag(np.diag(joint)), atol=1e-14)
        expected = prior.copy()
        expected[[0, -1]] = 0
        expected /= expected.sum()
        np.testing.assert_allclose(np.diag(joint), expected, atol=1e-14)

    def test_extreme_inventory_distribution_matches_direct_enumeration(self):
        prior = bayes.discretized_normal(2.0)
        direct = np.zeros((len(prior), len(prior)))
        for first, p_first in enumerate(prior):
            for second, p_second in enumerate(prior):
                maximum, minimum = max(first, second), min(first, second)
                if maximum >= 1 and minimum <= len(prior) - 2:
                    direct[maximum, minimum] += p_first * p_second
        direct /= direct.sum()
        np.testing.assert_allclose(bayes.joint_max_min(prior, 2), direct, atol=1e-14)

    def test_intensity_derivative_against_finite_difference(self):
        params = dynamic.Params()
        own = np.array([-0.4, 0.0, 0.5, 1.2])
        rival = np.array([0.2, 0.4, -0.1, 1.0])
        epsilon = 1e-6
        numerical = -(np.log(dynamic.f(own + epsilon, rival, params)) - np.log(dynamic.f(own - epsilon, rival, params))) / (2 * epsilon)
        np.testing.assert_allclose(dynamic.h(own, rival, params), numerical, rtol=1e-8, atol=1e-8)

    def test_uninformative_observation_preserves_prior(self):
        prior = bayes.discretized_normal(2.0)
        joint = bayes.joint_max_min(prior, 3)
        # Equal strategy-map values provide no inventory information at any noise level.
        post = bayes.posterior(joint, np.zeros(10), np.zeros(10), 0.0, 0.0, 0.1)
        np.testing.assert_allclose(post, joint, atol=1e-14)
        self.assertAlmostEqual(float(post.sum()), 1.0)


if __name__ == '__main__':
    unittest.main()
