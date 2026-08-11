############################################################
#  [*] Coefficients unit tests — locking the formulas
#
#  Pins the concentration metrics in
#  blnstats/calculations/coefficients.py (Coefficients) to
#  hand-checked values on shared inputs: uniform
#  [10,10,10,10], fully centralized [0,0,0,100], mixed
#  [5,15,25,55], plus the degenerate empty and all-zero
#  lists. Degenerate input must come back 0 (never a
#  division error); negative values must raise ValueError.
#
#  Used by:
#    - runTests.sh (repo root) — "python3 -m unittest discover"
#      over tests/test_*.py. pytest is installed in the
#      backend image but nothing invokes it, and no CI hook
#      runs this suite automatically.
############################################################


import unittest
import math
from blnstats.calculations.coefficients import Coefficients








############################################################
# TestCoefficients
############################################################
#
# One test per public Coefficients method, all working the
# same four canonical inputs so the metrics stay comparable.
#
#   test_calculate_gini / _hhi / _theil_index / _nakamoto /
#   _shannon_entropy        — full value + degenerate checks
#   test_calculate_normalized_*  — endpoint checks only
#   test_calculate_max_*         — the normalization ceilings
############################################################

class TestCoefficients(unittest.TestCase):






    ############################################################
    # setUp
    ############################################################
    #
    # Fresh Coefficients instance per test — the class holds
    # no state, so this is unittest convention, not necessity.
    #
    # Used by:
    #   - the unittest runner, before every test method
    ############################################################

    def setUp(self):
        self.coefficients = Coefficients()






    ############################################################
    # test_calculate_gini
    ############################################################
    #
    # Proves: uniform -> 0; one-of-four-holds-all -> (n-1)/n
    # = 0.75; [5,15,25,55] -> exactly 0.4; empty and all-zero
    # input -> 0.0 rather than a division error; negatives ->
    # ValueError.
    ############################################################

    def test_calculate_gini(self):
        # Uniform distribution (Gini should be 0)
        data_uniform = [10, 10, 10, 10]
        result = self.coefficients.calculate_gini(data_uniform)
        self.assertAlmostEqual(result, 0.0, places=5)

        # Single entity holds all value (Gini should be 0.75)
        data_centralized = [0, 0, 0, 100]
        result = self.coefficients.calculate_gini(data_centralized)
        self.assertAlmostEqual(result, 0.75, places=5)

        # Mixed values
        data_mixed = [5, 15, 25, 55]
        result = self.coefficients.calculate_gini(data_mixed)
        expected_result = 0.4  # exact: 2*(1*5+2*15+3*25+4*55)/(4*100) - 5/4
        self.assertAlmostEqual(result, expected_result, places=5)

        # Empty data
        data_empty = []
        result = self.coefficients.calculate_gini(data_empty)
        self.assertEqual(result, 0.0)

        # All zeros
        data_zeros = [0, 0, 0, 0]
        result = self.coefficients.calculate_gini(data_zeros)
        self.assertEqual(result, 0.0)

        # Negative values (should raise ValueError)
        data_negative = [10, -5, 15]
        with self.assertRaises(ValueError):
            self.coefficients.calculate_gini(data_negative)






    ############################################################
    # test_calculate_hhi
    ############################################################
    #
    # Proves: uniform -> the floor 10000/n = 2500; single
    # holder -> 10000; [5,15,25,55] -> 3900 (percent shares
    # squared: 25+225+625+3025); empty / all-zero -> 0.0;
    # negatives -> ValueError. The mixed case asserts with
    # places=0 (tolerates ±0.5) although the value is exact.
    ############################################################

    def test_calculate_hhi(self):
        # Uniform distribution (HHI should be minimum)
        data_uniform = [10, 10, 10, 10]
        result = self.coefficients.calculate_hhi(data_uniform)
        expected_result = 2500.0  # (1/n) * 10000
        self.assertAlmostEqual(result, expected_result, places=5)

        # Single entity holds all value (HHI should be 10000)
        data_centralized = [0, 0, 0, 100]
        result = self.coefficients.calculate_hhi(data_centralized)
        self.assertEqual(result, 10000.0)

        # Mixed values
        data_mixed = [5, 15, 25, 55]
        result = self.coefficients.calculate_hhi(data_mixed)
        expected_result = 3900.0  # exact: 5^2+15^2+25^2+55^2 on percent shares
        self.assertAlmostEqual(result, expected_result, places=0)

        # Empty data
        data_empty = []
        result = self.coefficients.calculate_hhi(data_empty)
        self.assertEqual(result, 0.0)

        # All zeros
        data_zeros = [0, 0, 0, 0]
        result = self.coefficients.calculate_hhi(data_zeros)
        self.assertEqual(result, 0.0)

        # Negative values (should raise ValueError)
        data_negative = [10, -5, 15]
        with self.assertRaises(ValueError):
            self.coefficients.calculate_hhi(data_negative)






    ############################################################
    # test_calculate_theil_index
    ############################################################
    #
    # Proves: uniform -> 0; single holder hits the ceiling
    # calculate_max_theil_index(n) = ln(n); mixed -> ~0.2766;
    # empty / all-zero -> 0.0; negatives -> ValueError.
    ############################################################

    def test_calculate_theil_index(self):
        # Uniform distribution (Theil Index should be 0)
        data_uniform = [10, 10, 10, 10]
        result = self.coefficients.calculate_theil_index(data_uniform)
        self.assertAlmostEqual(result, 0.0, places=5)

        # Single entity holds all value (Theil Index should be max)
        data_centralized = [0, 0, 0, 100]
        result = self.coefficients.calculate_theil_index(data_centralized)
        max_theil = self.coefficients.calculate_max_theil_index(len(data_centralized))
        self.assertAlmostEqual(result, max_theil, places=5)

        # Mixed values
        data_mixed = [5, 15, 25, 55]
        result = self.coefficients.calculate_theil_index(data_mixed)
        expected_result = 0.2766  # Approximate value
        self.assertAlmostEqual(result, expected_result, places=3)

        # Empty data
        data_empty = []
        result = self.coefficients.calculate_theil_index(data_empty)
        self.assertEqual(result, 0.0)

        # All zeros
        data_zeros = [0, 0, 0, 0]
        result = self.coefficients.calculate_theil_index(data_zeros)
        self.assertEqual(result, 0.0)

        # Negative values (should raise ValueError)
        data_negative = [5, -10, 15]
        with self.assertRaises(ValueError):
            self.coefficients.calculate_theil_index(data_negative)






    ############################################################
    # test_calculate_normalized_theil_index
    ############################################################
    #
    # Endpoint checks only — uniform -> 0, single holder ->
    # 1. Mixed, empty and negative inputs are only covered
    # for the raw index above, not for the normalized form.
    ############################################################

    def test_calculate_normalized_theil_index(self):
        # Uniform distribution (Normalized Theil Index should be 0)
        data_uniform = [10, 10, 10, 10]
        result = self.coefficients.calculate_normalized_theil_index(data_uniform)
        self.assertAlmostEqual(result, 0.0, places=5)

        # Single entity holds all value (Normalized Theil Index should be 1)
        data_centralized = [0, 0, 0, 100]
        result = self.coefficients.calculate_normalized_theil_index(data_centralized)
        self.assertAlmostEqual(result, 1.0, places=5)






    ############################################################
    # test_calculate_shannon_entropy
    ############################################################
    #
    # Proves: uniform hits the ceiling
    # calculate_max_shannon_entropy(n) = log2(n); single
    # holder -> 0; mixed -> ~1.601 bits; empty / all-zero ->
    # 0.0. GAP: unlike the other metrics there is no
    # negative-input ValueError case here.
    ############################################################

    def test_calculate_shannon_entropy(self):
        # Uniform distribution (Entropy should be maximum)
        data_uniform = [10, 10, 10, 10]
        result = self.coefficients.calculate_shannon_entropy(data_uniform)
        max_entropy = self.coefficients.calculate_max_shannon_entropy(len(data_uniform))
        self.assertAlmostEqual(result, max_entropy, places=5)

        # Single entity holds all value (Entropy should be 0)
        data_centralized = [0, 0, 0, 100]
        result = self.coefficients.calculate_shannon_entropy(data_centralized)
        self.assertAlmostEqual(result, 0.0, places=5)

        # Mixed values
        data_mixed = [5, 15, 25, 55]
        result = self.coefficients.calculate_shannon_entropy(data_mixed)
        expected_result = 1.601  # Approximate value
        self.assertAlmostEqual(result, expected_result, places=3)

        # Empty data
        data_empty = []
        result = self.coefficients.calculate_shannon_entropy(data_empty)
        self.assertEqual(result, 0.0)

        # All zeros
        data_zeros = [0, 0, 0, 0]
        result = self.coefficients.calculate_shannon_entropy(data_zeros)
        self.assertEqual(result, 0.0)






    ############################################################
    # test_calculate_normalized_shannon_entropy
    ############################################################
    #
    # Endpoint checks only — uniform -> 1 (maximum evenness),
    # single holder -> 0. Mixed and degenerate inputs are
    # only covered for the raw entropy above.
    ############################################################

    def test_calculate_normalized_shannon_entropy(self):
        # Uniform distribution (Normalized Entropy should be 1)
        data_uniform = [10, 10, 10, 10]
        result = self.coefficients.calculate_normalized_shannon_entropy(data_uniform)
        self.assertAlmostEqual(result, 1.0, places=5)

        # Single entity holds all value (Normalized Entropy should be 0)
        data_centralized = [0, 0, 0, 100]
        result = self.coefficients.calculate_normalized_shannon_entropy(data_centralized)
        self.assertAlmostEqual(result, 0.0, places=5)






    ############################################################
    # test_calculate_nakamoto
    ############################################################
    #
    # Proves the smallest set controlling over 51%: uniform
    # n=4 -> 3 (two shares are exactly 50%, not enough); a
    # dominant 55% share -> 1; single holder -> 1; empty /
    # all-zero -> 0; negatives -> ValueError.
    ############################################################

    def test_calculate_nakamoto(self):
        # Uniform distribution (Nakamoto Coefficient should be ceil(0.51 * n))
        data_uniform = [10, 10, 10, 10]
        result = self.coefficients.calculate_nakamoto(data_uniform)
        expected_result = 3  # 3 nodes needed to reach over 51%
        self.assertEqual(result, expected_result)

        # Single entity holds all value (Nakamoto Coefficient should be 1)
        data_centralized = [100, 0, 0, 0]
        result = self.coefficients.calculate_nakamoto(data_centralized)
        self.assertEqual(result, 1)

        # Mixed values
        data_mixed = [55, 25, 15, 5]
        result = self.coefficients.calculate_nakamoto(data_mixed)
        self.assertEqual(result, 1)

        # All zeros (Nakamoto Coefficient should be 0)
        data_zeros = [0, 0, 0, 0]
        result = self.coefficients.calculate_nakamoto(data_zeros)
        self.assertEqual(result, 0)

        # Empty data (Nakamoto Coefficient should be 0)
        data_empty = []
        result = self.coefficients.calculate_nakamoto(data_empty)
        self.assertEqual(result, 0)

        # Negative values (should raise ValueError)
        data_negative = [10, -5, 15]
        with self.assertRaises(ValueError):
            self.coefficients.calculate_nakamoto(data_negative)






    ############################################################
    # test_calculate_max_theil_index
    ############################################################
    #
    # The Theil normalization ceiling: ln(n) for n > 1, 0 for
    # n <= 1. Natural log here versus log2 for Shannon below
    # — the base difference is intentional (Theil in nats,
    # entropy in bits).
    ############################################################

    def test_calculate_max_theil_index(self):
        # n <= 1 should return 0
        result = self.coefficients.calculate_max_theil_index(1)
        self.assertEqual(result, 0.0)

        # n > 1
        result = self.coefficients.calculate_max_theil_index(4)
        expected_result = math.log(4)
        self.assertAlmostEqual(result, expected_result, places=5)






    ############################################################
    # test_calculate_max_shannon_entropy
    ############################################################
    #
    # The entropy ceiling: log2(n) for n > 1, 0 for n <= 1 —
    # bits, not nats (see the Theil ceiling above).
    ############################################################

    def test_calculate_max_shannon_entropy(self):
        # n <= 1 should return 0
        result = self.coefficients.calculate_max_shannon_entropy(1)
        self.assertEqual(result, 0.0)

        # n > 1
        result = self.coefficients.calculate_max_shannon_entropy(4)
        expected_result = math.log2(4)
        self.assertAlmostEqual(result, expected_result, places=5)








############################################################
# __main__ — direct execution
############################################################
#
# Lets "python3 tests/test_coefficients.py" run the suite
# without the shell script; discovery via runTests.sh is the
# normal path.
############################################################

if __name__ == '__main__':
    unittest.main()
