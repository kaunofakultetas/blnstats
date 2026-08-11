############################################################
#  [*] Channel-lifetime tests — bucketing math + contracts
#
#  The two channel-lifetime workflows in
#  calculations/general_stats.py, DB stubbed via db_fakes,
#  output read back from the hardcoded
#  /DATA/GENERATED/General_Stats/Channel_Lifetime/ path
#  (created inside the throwaway test container). Regular
#  tests pin the blocks->days bucketing (144 blocks/day,
#  floor) and the JSON payloads; the expectedFailure tests
#  pin three found bugs: the average query's WHERE missing
#  the histogram's same-block/inverted-row filter, the
#  method returning a raw SQL Decimal instead of the float
#  it writes, and GeneralStats.calculate crashing on the
#  half-integer channel counts that arise when one channel
#  endpoint is missing from a snapshot.
#
#  Used by:
#    - backend/runTests.sh — "python3 -m unittest discover"
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
# The found bugs, asserted correct-side-up.
#
#   test_average_and_histogram_filters_match (expectedFailure)
#   test_average_returns_float               (expectedFailure)
#   test_fractional_channel_count_survives   (expectedFailure)
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
    # Proves (intended contract): the method returns the same
    # float it writes into the JSON. Currently it returns the
    # raw SQL Decimal (or None on an empty table) while the
    # file says float — callers comparing the two get a
    # type surprise.
    ############################################################

    @unittest.expectedFailure
    def test_average_returns_float(self):
        result = [{'AverageChannelLifetime': Decimal('288.0')}]
        with patch.object(general_stats, 'get_db_connection', lambda: FakeConn(result, [])):
            ret = GeneralStats().calculate_channel_lifetime_average()
        self.assertIsInstance(ret, float)






    ############################################################
    # test_fractional_channel_count_survives
    ############################################################
    #
    # Proves (intended contract): a snapshot where one channel
    # endpoint is missing (its peer absent from the vertex
    # set) produces a half-integer channel count after the /2
    # halving — 3/2 = 1.5 here. GeneralStatsData declares
    # channel_count as int, so pydantic rejects 1.5 and the
    # whole stats build crashes with a ValidationError instead
    # of reporting the honest fractional count.
    ############################################################

    @unittest.expectedFailure
    def test_fractional_channel_count_survives(self):
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

        stats = GeneralStats().calculate(capacity, counts)
        self.assertEqual(stats.data['500000'].channel_count, 1.5)








if __name__ == '__main__':
    unittest.main()
