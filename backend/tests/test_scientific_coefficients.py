############################################################
#  [*] Scientific coefficient tests — invariants + bug pins
#
#  Goes beyond test_coefficients.py's spot values: checks
#  the mathematical properties every concentration metric
#  must hold (scale/permutation invariance, bounds,
#  normalization identities, concentration ordering), pins
#  textbook values computed by hand, and — in
#  TestKnownMetricBugs — asserts the CORRECT behavior for
#  the known metric bugs under @unittest.expectedFailure:
#  the suite stays green today, and the moment someone
#  fixes a metric the test flips to "unexpected success",
#  forcing the change to be acknowledged (these values are
#  published — silent shifts are the enemy).
#
#  Used by:
#    - runTests.sh (repo root) — "python3 -m unittest discover"
#      over tests/test_*.py
############################################################


import unittest
import math
from blnstats.calculations.coefficients import Coefficients
from blnstats.data_types import VerticesAspectDataStructure


# Shared datasets. IRREGULAR has n=12 (top-10% index 1) and
# no zeros so the normalization identities hold exactly;
# CONCENTRATED redistributes the same total 608 onto one
# holder, so ordering tests compare like with like.
IRREGULAR = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
CONCENTRATED = [1] * 11 + [597]








############################################################
# TestKnownValues
############################################################
#
# Hand-computed textbook values, exact where the formula is
# exact.
#
#   test_gini_arithmetic_sequence — 1..5 -> 4/15
#   test_theil_known              — [1,1,4] analytic
#   test_shannon_uniform_bits     — uniform 4 -> 2 bits
#   test_fully_centralized        — normalized endpoints
#   test_nakamoto_textbook        — the >50% cases that the
#                                   0.51 cutoff gets right
#   test_top10_decile_values      — n=10 and n=20
############################################################

class TestKnownValues(unittest.TestCase):






    ############################################################
    # setUp
    ############################################################
    #
    # Fresh instance per test (stateless; unittest convention).
    #
    # Used by:
    #   - the unittest runner, before every test method
    ############################################################

    def setUp(self):
        self.c = Coefficients()






    ############################################################
    # test_gini_arithmetic_sequence
    ############################################################
    #
    # Proves: Gini(1..5) = 4/15 — the exact discrete-formula
    # value (2*55/(5*15) - 6/5), independent of any sampling
    # convention.
    ############################################################

    def test_gini_arithmetic_sequence(self):
        self.assertAlmostEqual(self.c.calculate_gini([1, 2, 3, 4, 5]), 4 / 15, places=12)






    ############################################################
    # test_theil_known
    ############################################################
    #
    # Proves: Theil([1,1,4]) = (1/3)[2*(1/2)ln(1/2)] +
    # (2/3)ln 2 = ln 2 / 3 exactly.
    ############################################################

    def test_theil_known(self):
        self.assertAlmostEqual(self.c.calculate_theil_index([1, 1, 4]), math.log(2) / 3, places=12)






    ############################################################
    # test_shannon_uniform_bits
    ############################################################
    #
    # Proves: a uniform 4-way split carries exactly 2 bits,
    # which is also the ceiling log2(4) — entropy is in BITS
    # here, not nats.
    ############################################################

    def test_shannon_uniform_bits(self):
        self.assertAlmostEqual(self.c.calculate_shannon_entropy([10, 10, 10, 10]), 2.0, places=12)
        self.assertAlmostEqual(self.c.calculate_max_shannon_entropy(4), 2.0, places=12)






    ############################################################
    # test_fully_centralized
    ############################################################
    #
    # Proves: one holder with everything (zeros count toward
    # n) maxes normalized Theil at 1 and zeroes entropy —
    # the two normalized series must anchor opposite ends.
    ############################################################

    def test_fully_centralized(self):
        self.assertAlmostEqual(self.c.calculate_normalized_theil_index([0, 0, 0, 100]), 1.0, places=12)
        self.assertAlmostEqual(self.c.calculate_shannon_entropy([0, 0, 0, 100]), 0.0, places=12)
        self.assertAlmostEqual(self.c.calculate_normalized_shannon_entropy([0, 0, 0, 100]), 0.0, places=12)






    ############################################################
    # test_nakamoto_textbook
    ############################################################
    #
    # Proves: the cases where the current 0.51 cutoff agrees
    # with the textbook ">50% of capacity" definition —
    # 51/49 needs one holder, an exact 50/50 needs both, a
    # uniform four-way split needs three. (The disagreement
    # window lives in TestKnownMetricBugs.)
    ############################################################

    def test_nakamoto_textbook(self):
        self.assertEqual(self.c.calculate_nakamoto([51, 49]), 1)
        self.assertEqual(self.c.calculate_nakamoto([50, 50]), 2)
        self.assertEqual(self.c.calculate_nakamoto([10, 10, 10, 10]), 3)






    ############################################################
    # test_top10_decile_values
    ############################################################
    #
    # Proves: with n=10 the top decile is exactly the largest
    # holder (share as a 0-1 FRACTION, despite the method
    # name), with n=20 the largest two; the _sum variant
    # returns the same numerator un-divided.
    ############################################################

    def test_top10_decile_values(self):
        ten = [100, 1, 1, 1, 1, 1, 1, 1, 1, 1]  # total 109
        self.assertAlmostEqual(self.c.calculate_top_10_percent_control_percentage(ten), 100 / 109, places=12)
        self.assertAlmostEqual(self.c.calculate_top_10_percent_control_sum(ten), 100, places=12)

        twenty = [50, 30] + [1] * 18  # total 98, top two = 80
        self.assertAlmostEqual(self.c.calculate_top_10_percent_control_percentage(twenty), 80 / 98, places=12)
        self.assertAlmostEqual(self.c.calculate_top_10_percent_control_sum(twenty), 80, places=12)






    ############################################################
    # test_top10_negative_raises
    ############################################################
    #
    # Proves: both top-10% methods reject negative values like
    # every other metric ("nothing tests this at the moment"
    # no longer true).
    ############################################################

    def test_top10_negative_raises(self):
        with self.assertRaises(ValueError):
            self.c.calculate_top_10_percent_control_percentage([-1] + [1] * 11)
        with self.assertRaises(ValueError):
            self.c.calculate_top_10_percent_control_sum([-1] + [1] * 11)








############################################################
# TestInvariants
############################################################
#
# Properties that must hold for ANY valid input — these are
# what silently break under refactors.
#
#   test_scale_invariance        — shares-based metrics
#   test_permutation_invariance  — order must not matter
#   test_bounds                  — every metric in range
#   test_normalization_identity  — normalized = raw / max
#   test_concentration_ordering  — more concentrated moves
#                                  every metric the right way
############################################################

class TestInvariants(unittest.TestCase):






    ############################################################
    # setUp
    ############################################################
    #
    # Fresh instance per test (stateless; unittest convention).
    #
    # Used by:
    #   - the unittest runner, before every test method
    ############################################################

    def setUp(self):
        self.c = Coefficients()






    ############################################################
    # test_scale_invariance
    ############################################################
    #
    # Proves: multiplying every holding by 1000 (sats -> BTC
    # style rescale) changes NO metric except the top-10% SUM,
    # which scales linearly by design.
    ############################################################

    def test_scale_invariance(self):
        scaled = [v * 1000 for v in IRREGULAR]
        for metric in ('calculate_gini', 'calculate_hhi', 'calculate_theil_index',
                       'calculate_normalized_theil_index', 'calculate_shannon_entropy',
                       'calculate_normalized_shannon_entropy',
                       'calculate_top_10_percent_control_percentage'):
            with self.subTest(metric=metric):
                fn = getattr(self.c, metric)
                self.assertAlmostEqual(fn(IRREGULAR), fn(scaled), places=10)

        self.assertEqual(self.c.calculate_nakamoto(IRREGULAR), self.c.calculate_nakamoto(scaled))
        self.assertAlmostEqual(self.c.calculate_top_10_percent_control_sum(scaled),
                               1000 * self.c.calculate_top_10_percent_control_sum(IRREGULAR), places=6)






    ############################################################
    # test_permutation_invariance
    ############################################################
    #
    # Proves: input order never matters — every metric sorts
    # (or shares away) internally.
    ############################################################

    def test_permutation_invariance(self):
        shuffled = IRREGULAR[::2] + IRREGULAR[1::2]
        for metric in ('calculate_gini', 'calculate_hhi', 'calculate_theil_index',
                       'calculate_shannon_entropy',
                       'calculate_top_10_percent_control_percentage',
                       'calculate_top_10_percent_control_sum'):
            with self.subTest(metric=metric):
                fn = getattr(self.c, metric)
                self.assertAlmostEqual(fn(IRREGULAR), fn(shuffled), places=10)

        self.assertEqual(self.c.calculate_nakamoto(IRREGULAR), self.c.calculate_nakamoto(shuffled))






    ############################################################
    # test_bounds
    ############################################################
    #
    # Proves: on nonempty positive data every metric stays in
    # its defined range: Gini [0,1), HHI (0,10000], Theil
    # [0, ln n], entropy [0, log2 n], normalized forms [0,1],
    # Nakamoto {1..n}, top-10% share [0,1].
    ############################################################

    def test_bounds(self):
        n = len(IRREGULAR)
        self.assertGreaterEqual(self.c.calculate_gini(IRREGULAR), 0.0)
        self.assertLess(self.c.calculate_gini(IRREGULAR), 1.0)

        self.assertGreater(self.c.calculate_hhi(IRREGULAR), 0.0)
        self.assertLessEqual(self.c.calculate_hhi(IRREGULAR), 10000.0)

        self.assertGreaterEqual(self.c.calculate_theil_index(IRREGULAR), 0.0)
        self.assertLessEqual(self.c.calculate_theil_index(IRREGULAR), math.log(n))

        self.assertGreaterEqual(self.c.calculate_shannon_entropy(IRREGULAR), 0.0)
        self.assertLessEqual(self.c.calculate_shannon_entropy(IRREGULAR), math.log2(n))

        for norm in (self.c.calculate_normalized_theil_index(IRREGULAR),
                     self.c.calculate_normalized_shannon_entropy(IRREGULAR)):
            self.assertGreaterEqual(norm, 0.0)
            self.assertLessEqual(norm, 1.0)

        nakamoto = self.c.calculate_nakamoto(IRREGULAR)
        self.assertGreaterEqual(nakamoto, 1)
        self.assertLessEqual(nakamoto, n)

        share = self.c.calculate_top_10_percent_control_percentage(IRREGULAR)
        self.assertGreaterEqual(share, 0.0)
        self.assertLessEqual(share, 1.0)






    ############################################################
    # test_normalization_identity
    ############################################################
    #
    # Proves: the normalized series are EXACTLY raw / ceiling
    # (Theil / ln n, entropy / log2 n) — if either side ever
    # changes convention alone, published normalized charts
    # silently diverge from the raw ones.
    ############################################################

    def test_normalization_identity(self):
        n = len(IRREGULAR)
        self.assertAlmostEqual(self.c.calculate_normalized_theil_index(IRREGULAR),
                               self.c.calculate_theil_index(IRREGULAR) / math.log(n), places=12)
        self.assertAlmostEqual(self.c.calculate_normalized_shannon_entropy(IRREGULAR),
                               self.c.calculate_shannon_entropy(IRREGULAR) / math.log2(n), places=12)






    ############################################################
    # test_concentration_ordering
    ############################################################
    #
    # Proves: concentrating the same total onto one holder
    # raises Gini/HHI/Theil/top-10%, lowers entropy, and
    # never raises the Nakamoto count.
    ############################################################

    def test_concentration_ordering(self):
        self.assertGreater(self.c.calculate_gini(CONCENTRATED), self.c.calculate_gini(IRREGULAR))
        self.assertGreater(self.c.calculate_hhi(CONCENTRATED), self.c.calculate_hhi(IRREGULAR))
        self.assertGreater(self.c.calculate_theil_index(CONCENTRATED), self.c.calculate_theil_index(IRREGULAR))
        self.assertGreater(self.c.calculate_top_10_percent_control_percentage(CONCENTRATED),
                           self.c.calculate_top_10_percent_control_percentage(IRREGULAR))
        self.assertLess(self.c.calculate_shannon_entropy(CONCENTRATED), self.c.calculate_shannon_entropy(IRREGULAR))
        self.assertLessEqual(self.c.calculate_nakamoto(CONCENTRATED), self.c.calculate_nakamoto(IRREGULAR))








############################################################
# TestDispatcherAndSeries
############################################################
#
#   test_dispatcher_routes_all — every published name routes
#     to its method; unknown names raise
#   test_series_calculation    — calculate_on_vertices_data
#     carries value/date/timestamp/provenance per height
############################################################

class TestDispatcherAndSeries(unittest.TestCase):






    ############################################################
    # setUp
    ############################################################
    #
    # Fresh instance per test (stateless; unittest convention).
    #
    # Used by:
    #   - the unittest runner, before every test method
    ############################################################

    def setUp(self):
        self.c = Coefficients()






    ############################################################
    # test_dispatcher_routes_all
    ############################################################
    #
    # Proves: each of the nine chart-facing names returns the
    # same value as the direct method call, and a typo'd name
    # raises ValueError instead of silently charting garbage.
    ############################################################

    def test_dispatcher_routes_all(self):
        pairs = {
            'Gini': self.c.calculate_gini,
            'HHI': self.c.calculate_hhi,
            'Theil': self.c.calculate_theil_index,
            'NormalizedTheil': self.c.calculate_normalized_theil_index,
            'ShannonEntropy': self.c.calculate_shannon_entropy,
            'NormalizedShannonEntropy': self.c.calculate_normalized_shannon_entropy,
            'Nakamoto': self.c.calculate_nakamoto,
            'Top10PercentControlPercentage': self.c.calculate_top_10_percent_control_percentage,
            'Top10PercentControlSum': self.c.calculate_top_10_percent_control_sum,
        }
        for name, fn in pairs.items():
            with self.subTest(name=name):
                self.assertAlmostEqual(self.c.calculate_coefficient(IRREGULAR, name), fn(IRREGULAR), places=12)

        with self.assertRaises(ValueError):
            self.c.calculate_coefficient(IRREGULAR, 'Ginny')






    ############################################################
    # test_series_calculation
    ############################################################
    #
    # Proves: running Gini over a two-height vertices
    # structure yields per-height values matching the direct
    # call, preserves date/timestamp, records the input
    # length/sum, and appends the input yAxis to the
    # provenance chain.
    ############################################################

    def test_series_calculation(self):
        vertices = VerticesAspectDataStructure(
            meta={
                'type': 'test', 'description': 'capacity per node',
                'updated': '2026-08-11', 'xAxis': 'Date',
                'yAxis': 'List(NodeID,Capacity)',
                'yAxisSupplyChain': ['BlockHeight'],
            },
            data={
                '500000': {'date': '2018-01-01', 'timestamp': 1514764800,
                           'vertices': [{'name': 'a', 'value': 10},
                                        {'name': 'b', 'value': 30}]},
                '510000': {'date': '2018-02-01', 'timestamp': 1517443200,
                           'vertices': [{'name': 'a', 'value': 20},
                                        {'name': 'b', 'value': 20}]},
            },
        )

        series = self.c.calculate_on_vertices_data(vertices, 'Gini')

        first = series.data['500000']
        self.assertAlmostEqual(first.value, self.c.calculate_gini([10, 30]), places=12)
        self.assertEqual(first.date, '2018-01-01')
        self.assertEqual(first.timestamp, 1514764800)
        self.assertEqual(first.input_array_length, 2)
        self.assertEqual(first.input_array_sum, 40)

        self.assertAlmostEqual(series.data['510000'].value, 0.0, places=12)  # equal split
        self.assertIn('List(NodeID,Capacity)', series.meta.yAxisSupplyChain)








############################################################
# TestKnownMetricBugs
############################################################
#
# Each test asserts the CORRECT scientific behavior. The
# top-10% cases are FIXED (never-empty decile + zero-total
# guard, values for n >= 10 unchanged) and now guard
# against regression. The Nakamoto cutoff stays pinned
# under @unittest.expectedFailure — fixing it changes
# published series, so the fix must be acknowledged by
# removing the decorator.
#
#   test_nakamoto_between_50_and_51_percent — 0.51 cutoff
#     (expectedFailure, pending review)
#   test_top10_small_network_controls_something — fixed
#   test_top10_sum_small_network                — fixed
#   test_top10_all_zero_is_zero                 — fixed
############################################################

class TestKnownMetricBugs(unittest.TestCase):






    ############################################################
    # setUp
    ############################################################
    #
    # Fresh instance per test (stateless; unittest convention).
    #
    # Used by:
    #   - the unittest runner, before every test method
    ############################################################

    def setUp(self):
        self.c = Coefficients()






    ############################################################
    # test_nakamoto_between_50_and_51_percent
    ############################################################
    #
    # Proves (textbook): a holder with 50.5% of capacity IS a
    # majority — Nakamoto must be 1. The 0.51 cutoff answers 2
    # for any top share in (50%, 51%), overcounting by one.
    ############################################################

    @unittest.expectedFailure
    def test_nakamoto_between_50_and_51_percent(self):
        self.assertEqual(self.c.calculate_nakamoto([505, 495]), 1)






    ############################################################
    # test_top10_small_network_controls_something
    ############################################################
    #
    # Proves: in any nonempty network the top decile controls
    # MORE than nothing — for n < 10 the decile is the single
    # largest holder (max(1, floor(0.1*n))), never an empty
    # set reporting "0% of capacity".
    ############################################################

    def test_top10_small_network_controls_something(self):
        self.assertGreater(self.c.calculate_top_10_percent_control_percentage([100, 1, 1, 1]), 0.0)






    ############################################################
    # test_top10_sum_small_network
    ############################################################
    #
    # Proves: the sum variant follows the same rule — the top
    # decile of [100,1,1,1] controls at least the largest
    # holder's 100.
    ############################################################

    def test_top10_sum_small_network(self):
        self.assertGreaterEqual(self.c.calculate_top_10_percent_control_sum([100, 1, 1, 1]), 100)






    ############################################################
    # test_top10_all_zero_is_zero
    ############################################################
    #
    # Proves: an all-zero network follows the same degenerate
    # convention as every other metric (-> 0.0) instead of
    # dividing 0/0 into numpy nan.
    ############################################################

    def test_top10_all_zero_is_zero(self):
        self.assertEqual(self.c.calculate_top_10_percent_control_percentage([0] * 12), 0.0)








if __name__ == '__main__':
    unittest.main()
