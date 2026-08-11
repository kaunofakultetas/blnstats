############################################################
#  [*] Scientific pipeline tests — Lorenz + network totals
#
#  The calculation layer AROUND the coefficients:
#  calculate_gini_from_lorenz in blnstats/__init__.py (the
#  printed cross-check for the Lorenz charts) and
#  GeneralStats.calculate (the published node/channel/
#  capacity totals, including the halve-the-double-count
#  and satoshi->BTC conventions). Known bugs are asserted
#  correct-side-up under @unittest.expectedFailure, as in
#  test_scientific_coefficients.py. Importing blnstats pulls
#  the whole package (matplotlib included) — fine inside the
#  backend image, where this suite runs.
#
#  Used by:
#    - backend/runTests.sh — "python3 -m unittest discover"
#      over tests/test_*.py
############################################################


import unittest
from blnstats import calculate_gini_from_lorenz
from blnstats.calculations.coefficients import Coefficients
from blnstats.calculations.general_stats import GeneralStats
from blnstats.data_types import VerticesAspectDataStructure


META_COMMON = {
    'type': 'test', 'description': 'unit test structure',
    'updated': '2026-08-11', 'xAxis': 'Date',
    'yAxisSupplyChain': ['BlockHeight'],
}


############################################################
# make_vertices
############################################################
#
# One VerticesAspectDataStructure with the given yAxis label
# and {height: [(name, value), ...]} data — the shape both
# GeneralStats tests feed in.
#
# Used by:
#   - TestGeneralStatsCalculate (below)
############################################################

def make_vertices(y_axis, per_height):
    return VerticesAspectDataStructure(
        meta={**META_COMMON, 'yAxis': y_axis},
        data={
            height: {'date': date, 'timestamp': ts,
                     'vertices': [{'name': n, 'value': v} for n, v in vertices]}
            for height, (date, ts, vertices) in per_height.items()
        },
    )








############################################################
# TestGiniFromLorenz
############################################################
#
#   test_perfect_equality_is_zero
#   test_known_curve            — hand-integrated trapezoid
#   test_matches_discrete_gini  — cross-check vs the exact
#                                 Coefficients formula
#   test_missing_origin_handled — the (0,0) fix-up path
#   test_missing_end_does_not_mutate_caller — the in-place
#                                 append bug (expectedFailure)
############################################################

class TestGiniFromLorenz(unittest.TestCase):






    ############################################################
    # test_perfect_equality_is_zero
    ############################################################
    #
    # Proves: the equality diagonal integrates to Gini 0.
    ############################################################

    def test_perfect_equality_is_zero(self):
        steps = [0, 25, 50, 75, 100]
        self.assertAlmostEqual(calculate_gini_from_lorenz(steps, list(steps)), 0.0, places=12)






    ############################################################
    # test_known_curve
    ############################################################
    #
    # Proves: the curve (0,0)-(50,20)-(100,100) has trapezoid
    # area 0.35, hence Gini 2*(0.5-0.35) = 0.3 exactly.
    ############################################################

    def test_known_curve(self):
        self.assertAlmostEqual(calculate_gini_from_lorenz([0, 50, 100], [0, 20, 100]), 0.3, places=12)






    ############################################################
    # test_matches_discrete_gini
    ############################################################
    #
    # Proves: a Lorenz polygon built from sorted data
    # [5,15,25,55] integrates to EXACTLY the discrete Gini of
    # the same data (0.4) — the trapezoid rule is exact on the
    # polygon, so the printed cross-check and the published
    # coefficient must agree to full precision, not just
    # roughly.
    ############################################################

    def test_matches_discrete_gini(self):
        data = [5, 15, 25, 55]  # total 100, cumulative 5,20,45,100
        percentiles = [25, 50, 75, 100]
        cumulative = [5, 20, 45, 100]
        self.assertAlmostEqual(calculate_gini_from_lorenz(percentiles, cumulative),
                               Coefficients().calculate_gini(data), places=12)






    ############################################################
    # test_missing_origin_handled
    ############################################################
    #
    # Proves: a curve arriving without its (0,0) point gets it
    # prepended (by rebinding — the CALLER's lists must stay
    # untouched) and integrates to the same 0.4.
    ############################################################

    def test_missing_origin_handled(self):
        percentiles = [25, 50, 75, 100]
        cumulative = [5, 20, 45, 100]
        self.assertAlmostEqual(calculate_gini_from_lorenz(percentiles, cumulative), 0.4, places=12)
        self.assertEqual(percentiles, [25, 50, 75, 100])
        self.assertEqual(cumulative, [5, 20, 45, 100])






    ############################################################
    # test_missing_end_does_not_mutate_caller
    ############################################################
    #
    # Proves: a curve arriving without its (100,100) endpoint
    # must ALSO leave the caller's lists untouched. Currently
    # that path appends IN PLACE (asymmetric with the origin
    # fix-up), so a caller reusing its list for plotting would
    # draw a phantom endpoint. Never fires with today's sole
    # caller — this pins the contract for the next one.
    ############################################################

    @unittest.expectedFailure
    def test_missing_end_does_not_mutate_caller(self):
        percentiles = [0, 25, 50]
        cumulative = [0, 5, 20]
        calculate_gini_from_lorenz(percentiles, cumulative)
        self.assertEqual(percentiles, [0, 25, 50])
        self.assertEqual(cumulative, [0, 5, 20])








############################################################
# TestGeneralStatsCalculate
############################################################
#
#   test_totals            — the /2 double-count halving and
#                            satoshi -> BTC conversion
#   test_label_guards      — wrong yAxis labels raise
#   test_length_guard      — mismatched series length raises
#   test_endpoint_guard    — mismatched first height raises
#   test_mid_series_mismatch_raises — the guard hole
#                            (expectedFailure)
############################################################

class TestGeneralStatsCalculate(unittest.TestCase):






    ############################################################
    # __capacity / __counts
    ############################################################
    #
    # Matched two-height inputs: two nodes reporting the same
    # channel from both ends (values are per-node sums, so
    # network totals are exactly half).
    #
    # Used by:
    #   - every test in this class (below)
    ############################################################

    def __capacity(self, heights=('500000', '510000')):
        return make_vertices('List(NodeID,Capacity)', {
            heights[0]: ('2018-01-01', 1514764800, [('a', 200000000), ('b', 400000000)]),
            heights[1]: ('2018-02-01', 1517443200, [('a', 600000000), ('b', 600000000)]),
        })

    def __counts(self, heights=('500000', '510000')):
        return make_vertices('List(NodeID,ChannelCount)', {
            heights[0]: ('2018-01-01', 1514764800, [('a', 2), ('b', 4)]),
            heights[1]: ('2018-02-01', 1517443200, [('a', 4), ('b', 4)]),
        })






    ############################################################
    # test_totals
    ############################################################
    #
    # Proves: capacities [2e8, 4e8] sats become 3.0 BTC of
    # network capacity (sum / 2 endpoints / 1e8 sats), channel
    # counts [2, 4] become 3 channels, and node_count is the
    # vertex count — per height.
    ############################################################

    def test_totals(self):
        stats = GeneralStats().calculate(self.__capacity(), self.__counts())

        first = stats.data['500000']
        self.assertEqual(first.node_count, 2)
        self.assertAlmostEqual(first.network_capacity, 3.0, places=12)
        self.assertEqual(first.channel_count, 3)

        second = stats.data['510000']
        self.assertAlmostEqual(second.network_capacity, 6.0, places=12)
        self.assertEqual(second.channel_count, 4)






    ############################################################
    # test_label_guards
    ############################################################
    #
    # Proves: swapping the two inputs (wrong yAxis labels)
    # raises instead of silently averaging capacities as
    # channel counts.
    ############################################################

    def test_label_guards(self):
        with self.assertRaises(ValueError):
            GeneralStats().calculate(self.__counts(), self.__capacity())






    ############################################################
    # test_length_guard
    ############################################################
    #
    # Proves: series of different lengths raise.
    ############################################################

    def test_length_guard(self):
        counts = self.__counts()
        counts.data.pop('510000')
        with self.assertRaises(ValueError):
            GeneralStats().calculate(self.__capacity(), counts)






    ############################################################
    # test_endpoint_guard
    ############################################################
    #
    # Proves: series starting at different block heights raise
    # even when lengths match.
    ############################################################

    def test_endpoint_guard(self):
        with self.assertRaises(ValueError):
            GeneralStats().calculate(self.__capacity(), self.__counts(heights=('499999', '510000')))






    ############################################################
    # test_mid_series_mismatch_raises
    ############################################################
    #
    # Proves: a MID-series height mismatch (same length, same
    # first and last height) must also raise — the capacity of
    # one block would otherwise be paired with the channel
    # count of a different one. The current guard compares
    # only the endpoints, so this slips through and produces a
    # misaligned published series.
    ############################################################

    @unittest.expectedFailure
    def test_mid_series_mismatch_raises(self):
        capacity = make_vertices('List(NodeID,Capacity)', {
            '500000': ('2018-01-01', 1514764800, [('a', 200000000)]),
            '505000': ('2018-01-15', 1515974400, [('a', 200000000)]),
            '510000': ('2018-02-01', 1517443200, [('a', 200000000)]),
        })
        counts = make_vertices('List(NodeID,ChannelCount)', {
            '500000': ('2018-01-01', 1514764800, [('a', 2)]),
            '507000': ('2018-01-20', 1516406400, [('a', 2)]),
            '510000': ('2018-02-01', 1517443200, [('a', 2)]),
        })
        with self.assertRaises(ValueError):
            GeneralStats().calculate(capacity, counts)








if __name__ == '__main__':
    unittest.main()
