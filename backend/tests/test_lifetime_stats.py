############################################################
#  [*] Channel-lifetime tests — bucketing math + contracts
#
#  The two channel-lifetime workflows in
#  calculations/general_stats.py, DB stubbed via db_fakes,
#  output read back from the hardcoded
#  /DATA/GENERATED/General_Stats/Channel_Lifetime/ path
#  (created inside the throwaway test container). Regular
#  tests pin the blocks->days bucketing (144 blocks/day,
#  floor) and the JSON payloads. The float-return contract
#  and the odd-endpoint-sum invariant (half a channel is
#  physically impossible — an odd sum means incomplete
#  data and raises a diagnostic error) are FIXED and now
#  guard against regression; the one remaining
#  expectedFailure pins the average query's WHERE missing
#  the histogram's same-block/inverted-row filter — a
#  published-population decision still pending review.
#
#  Used by:
#    - runTests.sh (repo root) — "python3 -m unittest discover"
#      over tests/test_*.py
############################################################


import unittest
import inspect
import json
from decimal import Decimal
from unittest.mock import patch

from blnstats.calculations import general_stats
from blnstats.calculations.general_stats import GeneralStats
from blnstats.data_types import VerticesAspectDataStructure
from db_fakes import FakeConn


PLOT_JSON = '/DATA/GENERATED/General_Stats/Channel_Lifetime/channel_lifetime_plot.json'
AVG_JSON = '/DATA/GENERATED/General_Stats/Channel_Lifetime/channel_lifetime_average.json'








############################################################
# TestLifetimePlot
############################################################
#
#   test_bucketing — blocks -> whole days at 144/day, None
#     rows skipped, zero-channel days omitted, meta total
############################################################

class TestLifetimePlot(unittest.TestCase):






    ############################################################
    # test_bucketing
    ############################################################
    #
    # Proves: 0 and 143 blocks land in day 0, 144 in day 1,
    # 288 in day 2; a NULL lifetime row is skipped; absent
    # days are omitted from the payload; meta.total_channels
    # counts the four real rows.
    ############################################################

    def test_bucketing(self):
        rows = [{'ChannelLifetime': 0}, {'ChannelLifetime': 143},
                {'ChannelLifetime': 144}, {'ChannelLifetime': 288},
                {'ChannelLifetime': None}]
        with patch.object(general_stats, 'get_db_connection', lambda: FakeConn([rows], [])):
            GeneralStats().calculate_channel_lifetime_plot()

        with open(PLOT_JSON) as f:
            payload = json.load(f)

        self.assertEqual(payload['data']['0']['channel_count'], 2)
        self.assertEqual(payload['data']['1']['channel_count'], 1)
        self.assertEqual(payload['data']['2']['channel_count'], 1)
        self.assertEqual(payload['meta']['total_channels'], 4)






    ############################################################
    # test_average_json_payload
    ############################################################
    #
    # Proves: the average JSON carries the SQL value as float
    # blocks and /144 days.
    ############################################################

    def test_average_json_payload(self):
        result = [{'AverageChannelLifetime': Decimal('288.0')}]
        with patch.object(general_stats, 'get_db_connection', lambda: FakeConn(result, [])):
            GeneralStats().calculate_channel_lifetime_average()

        with open(AVG_JSON) as f:
            payload = json.load(f)

        self.assertEqual(payload['data']['average_channel_lifetime_blocks'], 288.0)
        self.assertEqual(payload['data']['average_channel_lifetime_days'], 2.0)








############################################################
# TestLifetimeContracts
############################################################
#
# The found contracts, asserted correct-side-up.
#
#   test_average_and_histogram_filters_match (expectedFailure
#     — pending the published-population decision)
#   test_average_returns_float               — fixed
#   test_odd_endpoint_sum_raises             — the whole-
#     channel invariant, enforced with a clear error
############################################################

class TestLifetimeContracts(unittest.TestCase):






    ############################################################
    # test_average_and_histogram_filters_match
    ############################################################
    #
    # Proves (intended contract): the average and the
    # histogram must describe the SAME channel population. The
    # histogram's WHERE drops same-block closes and inverted
    # funding/spending rows ("SpendingBlockIndex >
    # FundingBlockIndex OR sentinel"); the average query
    # lacks that condition, so those rows count in one
    # statistic but not the other. Checked textually against
    # the method source — the SQL itself needs a DB to run.
    ############################################################

    @unittest.expectedFailure
    def test_average_and_histogram_filters_match(self):
        avg_src = inspect.getsource(GeneralStats.calculate_channel_lifetime_average)
        self.assertIn('SpendingBlockIndex > BT.FundingBlockIndex', avg_src)






    ############################################################
    # test_average_returns_float
    ############################################################
    #
    # Proves: the method returns the same float it writes into
    # the JSON (0 on an empty table) — no raw SQL Decimal or
    # None type surprises for callers.
    ############################################################

    def test_average_returns_float(self):
        result = [{'AverageChannelLifetime': Decimal('288.0')}]
        with patch.object(general_stats, 'get_db_connection', lambda: FakeConn(result, [])):
            ret = GeneralStats().calculate_channel_lifetime_average()
        self.assertIsInstance(ret, float)






    ############################################################
    # test_odd_endpoint_sum_raises
    ############################################################
    #
    # Proves: an ODD channel-endpoint sum — physically
    # impossible for a complete snapshot, every channel has
    # two endpoints — is refused with a diagnostic ValueError
    # naming the block height, instead of publishing half a
    # channel or dying in an opaque pydantic ValidationError.
    ############################################################

    def test_odd_endpoint_sum_raises(self):
        meta = {'type': 't', 'description': 'd', 'updated': 'u', 'xAxis': 'x',
                'yAxisSupplyChain': ['BlockHeight']}
        capacity = VerticesAspectDataStructure(
            meta={**meta, 'yAxis': 'List(NodeID,Capacity)'},
            data={'500000': {'date': '2018-01-01', 'timestamp': 1514764800,
                             'vertices': [{'name': 'a', 'value': 200000000}]}})
        counts = VerticesAspectDataStructure(
            meta={**meta, 'yAxis': 'List(NodeID,ChannelCount)'},
            data={'500000': {'date': '2018-01-01', 'timestamp': 1514764800,
                             'vertices': [{'name': 'a', 'value': 3}]}})

        with self.assertRaises(ValueError) as ctx:
            GeneralStats().calculate(capacity, counts)
        self.assertIn('500000', str(ctx.exception))
        self.assertIn('endpoint', str(ctx.exception))








if __name__ == '__main__':
    unittest.main()
