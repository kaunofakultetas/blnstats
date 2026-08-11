############################################################
#  [*] Property tests — fuzzed cross-checks + workflow glue
#
#  Seeded randomized cross-validation of the scientific
#  layer (deterministic — random.Random(42), no test-run
#  flakiness): every fuzzed dataset must yield the SAME
#  Gini through the discrete formula and through its own
#  Lorenz polygon, satisfy the metric inequalities, and
#  round-trip satoshi amounts losslessly through the float
#  BTC representation the blockchain parser uses. The last
#  class drives the whole generateLorenzCharts workflow
#  with selectors and the chart renderer stubbed — its
#  expectedFailure pins the IndexError a zero-vertex
#  snapshot causes.
#
#  Used by:
#    - runTests.sh (repo root) — "python3 -m unittest discover"
#      over tests/test_*.py
############################################################


import unittest
import os
import random
from decimal import Decimal
from unittest.mock import patch, MagicMock

import blnstats
from blnstats import calculate_gini_from_lorenz
from blnstats.calculations.coefficients import Coefficients
from blnstats.data_types import VerticesAspectDataStructure


############################################################
# fuzz_datasets
############################################################
#
# 25 deterministic datasets: 1-60 holders, values 0-1e6,
# never all-zero. Seeded so a failure is reproducible.
#
# Used by:
#   - TestFuzzedMetricProperties (below)
############################################################

def fuzz_datasets(count=25, seed=42):
    rng = random.Random(seed)
    datasets = []
    for _ in range(count):
        n = rng.randint(1, 60)
        data = [rng.randint(0, 10 ** 6) for _ in range(n)]
        if sum(data) == 0:
            data[0] = 1
        datasets.append(data)
    return datasets








############################################################
# TestFuzzedMetricProperties
############################################################
#
#   test_lorenz_gini_agreement — the discrete formula and
#     the Lorenz-polygon integral are the same statistic
#   test_metric_inequalities   — HHI floor, Nakamoto
#     majority, Gini bounds and zero-padding monotonicity
############################################################

class TestFuzzedMetricProperties(unittest.TestCase):






    ############################################################
    # setUp
    ############################################################
    #
    # Shared Coefficients instance + the seeded datasets.
    #
    # Used by:
    #   - the unittest runner, before every test method
    ############################################################

    def setUp(self):
        self.c = Coefficients()
        self.datasets = fuzz_datasets()






    ############################################################
    # test_lorenz_gini_agreement
    ############################################################
    #
    # Proves: for every fuzzed dataset, building the Lorenz
    # polygon (sorted ascending, cumulative percentages) and
    # integrating it reproduces calculate_gini to 9 decimals —
    # the published coefficient and the published curve can
    # never drift apart.
    ############################################################

    def test_lorenz_gini_agreement(self):
        for data in self.datasets:
            with self.subTest(n=len(data)):
                sorted_data = sorted(data)
                total = sum(sorted_data)
                running, cumulative = 0, []
                for value in sorted_data:
                    running += value
                    cumulative.append(running / total * 100)
                percentiles = [(i + 1) / len(sorted_data) * 100 for i in range(len(sorted_data))]

                self.assertAlmostEqual(calculate_gini_from_lorenz(percentiles, cumulative),
                                       self.c.calculate_gini(data), places=9)






    ############################################################
    # test_metric_inequalities
    ############################################################
    #
    # Proves, per fuzzed dataset: HHI never drops below its
    # uniform floor 10000/n; the Nakamoto set really holds a
    # majority (> 50%); Gini stays in [0, 1); and diluting
    # the network with empty holders never DECREASES Gini.
    ############################################################

    def test_metric_inequalities(self):
        for data in self.datasets:
            with self.subTest(n=len(data)):
                total = sum(data)
                n = len(data)

                self.assertGreaterEqual(self.c.calculate_hhi(data) + 1e-9, 10000.0 / n)

                nakamoto = self.c.calculate_nakamoto(data)
                top_sum = sum(sorted(data, reverse=True)[:nakamoto])
                self.assertGreater(top_sum, 0.5 * total)

                gini = self.c.calculate_gini(data)
                self.assertGreaterEqual(gini, 0.0)
                self.assertLess(gini, 1.0)
                self.assertGreaterEqual(self.c.calculate_gini(data + [0] * 5) + 1e-12, gini)








############################################################
# TestSatoshiRoundTrip
############################################################
#
#   test_lossless_for_bitcoin_range — the parser's float BTC
#     detour cannot corrupt any legal satoshi amount
############################################################

class TestSatoshiRoundTrip(unittest.TestCase):






    ############################################################
    # test_lossless_for_bitcoin_range
    ############################################################
    #
    # Proves: the exact conversion chain the blockchain parser
    # and worker use — satoshis -> float BTC (value/1e8) ->
    # Decimal(str(...)) -> int(x * 1e8) — is LOSSLESS for
    # every legal amount up to the full 21M BTC supply
    # (float64 holds integers exactly to 2^53 ≈ 9e15 sats,
    # comfortably above 2.1e15). Positive assurance: the
    # documented "lossy by construction" float detour is in
    # fact exact for Bitcoin's range.
    ############################################################

    def test_lossless_for_bitcoin_range(self):
        rng = random.Random(7)
        edge_cases = [1, 546, 9999, 100000000, 123456789, 2100000000000000]
        samples = edge_cases + [rng.randint(1, 2100000000000000) for _ in range(50)]

        for sats in samples:
            with self.subTest(sats=sats):
                value = sats / 100000000  # the parser's float BTC
                back = int(Decimal(str(value)) * Decimal('100000000'))
                self.assertEqual(back, sats)








############################################################
# TestLorenzChartWorkflow
############################################################
#
# Drives generateLorenzCharts end to end with the DB
# selectors stubbed and the chart renderer mocked — the
# JSON archives land under /DATA inside the test container.
#
#   test_workflow_completes      — happy path, archive files
#   test_empty_snapshot_survives — zero-vertex snapshot
#                                  (expectedFailure)
############################################################

class TestLorenzChartWorkflow(unittest.TestCase):






    ############################################################
    # __run_workflow
    ############################################################
    #
    # Patches RawDataSelector / NodeMetricsSelector /
    # EntityMetricsSelector to serve the given vertices and
    # LorenzCurveChartGenerator with a MagicMock, then runs
    # generateLorenzCharts.
    #
    # Used by:
    #   - both tests (below)
    ############################################################

    def __run_workflow(self, vertices):
        capacity = VerticesAspectDataStructure(
            meta={'type': 't', 'description': 'd', 'updated': 'u', 'xAxis': 'x',
                  'yAxis': 'List(NodeID,Capacity)', 'yAxisSupplyChain': ['BlockHeight']},
            data={'500000': {'date': '2018-03-01', 'timestamp': 1519862400,
                             'vertices': vertices}})
        counts = VerticesAspectDataStructure(
            meta={'type': 't', 'description': 'd', 'updated': 'u', 'xAxis': 'x',
                  'yAxis': 'List(NodeID,ChannelCount)', 'yAxisSupplyChain': ['BlockHeight']},
            data={'500000': {'date': '2018-03-01', 'timestamp': 1519862400,
                             'vertices': vertices}})

        class FakeRawSelector:
            def get_first_blocks_of_days_by_date_mask(self, **kwargs):
                return None  # only handed through to the metric selectors

        class FakeMetricsSelector:
            def get_capacity_metrics(self, heights):
                return capacity

            def get_channel_count_metrics(self, heights):
                return counts

        with patch.object(blnstats, 'RawDataSelector', FakeRawSelector), \
             patch.object(blnstats, 'NodeMetricsSelector', FakeMetricsSelector), \
             patch.object(blnstats, 'EntityMetricsSelector', FakeMetricsSelector), \
             patch.object(blnstats, 'LorenzCurveChartGenerator', MagicMock()):
            blnstats.generateLorenzCharts()






    ############################################################
    # test_workflow_completes
    ############################################################
    #
    # Proves: with real two-vertex snapshots the whole glue —
    # selector, JSON archive, Gini series, Lorenz dataset
    # build, chart calls — runs to completion and writes the
    # vertex archive.
    ############################################################

    def test_workflow_completes(self):
        self.__run_workflow([{'name': 'a', 'value': 10}, {'name': 'b', 'value': 30}])
        self.assertTrue(os.path.exists('/DATA/GENERATED/Nodes/weighted_degree/20XX-03-01.json'))






    ############################################################
    # test_empty_snapshot_survives
    ############################################################
    #
    # Proves (intended contract): a snapshot with ZERO
    # vertices — a month before the network existed, or a
    # gap in the cache — must be skipped, not kill the whole
    # chart run. Currently STEP 5's cumulative_sum[-1] raises
    # IndexError on the empty list.
    ############################################################

    @unittest.expectedFailure
    def test_empty_snapshot_survives(self):
        self.__run_workflow([])








if __name__ == '__main__':
    unittest.main()
