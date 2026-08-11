############################################################
#  [*] DB selector tests — real SQL against a real MySQL
#
#  The layer no fake can reach: the selector queries in
#  database/ and the lifetime SQL in general_stats.py, run
#  against the throwaway MySQL that runTests.sh boots from
#  mysql/init.sql (DB_* env vars point at it). Every test
#  wipes the data tables first, seeds its own fixture rows,
#  and asserts the actual SQL semantics: the date-mask
#  wildcard, the funding/spending activity window and its
#  boundary, endpoint double-crediting, the entity GROUP BY
#  with its COALESCE fallback (a node without an entity row
#  stands as its own entity), the lifetime average and
#  histogram sharing one channel population (proven with
#  live numbers), and the prefix-restricted entity-name
#  fixer sparing genuine hex-word aliases. Skips cleanly
#  when no DB is reachable (plain unit-test runs).
#
#  Used by:
#    - runTests.sh (repo root) — "python3 -m unittest
#      discover" over tests/test_*.py, with the throwaway
#      MySQL running
############################################################


import unittest
import json
from unittest import skipUnless

from blnstats.database.utils import get_db_connection, create_tables_if_not_exists
from blnstats.database.raw_data_selector import RawDataSelector
from blnstats.database.entity_metrics_selector import EntityMetricsSelector
from blnstats.calculations.general_stats import GeneralStats
from blnstats.data_types import BlockchainBlockHeightsStructure


############################################################
# DB availability probe
############################################################
#
# One connection attempt at import time — without the
# runTests.sh MySQL the whole module skips instead of
# erroring 20 times.
############################################################

try:
    _probe = get_db_connection()
    _probe.close()
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False


SENTINEL = 999999999  # SpendingBlockIndex value meaning "still open"








############################################################
# DBFixture
############################################################
#
# Shared base: wipes the data tables (FK-safe order) before
# every test and offers one-line seeders. System_* tables
# are left alone — the init.sql seeds stay.
############################################################

@skipUnless(DB_AVAILABLE, 'no test database reachable (run via runTests.sh)')
class DBFixture(unittest.TestCase):






    ############################################################
    # setUp
    ############################################################
    #
    # Child tables first so the FKs never block the wipe.
    #
    # Used by:
    #   - the unittest runner, before every test method
    ############################################################

    def setUp(self):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for table in ('Blockchain_Transactions', '_CACHED1_NodeMetrics',
                              'Lightning_Channels', 'Blockchain_Blocks',
                              'Lightning_Entities', 'Lightning_NodeAliases'):
                    cursor.execute(f'DELETE FROM `{table}`')
            conn.commit()






    ############################################################
    # seed helpers
    ############################################################
    #
    # Minimal-column INSERTs; irrelevant fields get dummies.
    #
    # Used by:
    #   - every test class below
    ############################################################

    def seed_block(self, height, date, timestamp=1514764800):
        self.__execute('INSERT INTO Blockchain_Blocks (BlockHeight, BlockHash, Timestamp, Time, Date) '
                       'VALUES (%s, %s, %s, %s, %s)',
                       (height, 'ff' * 32, timestamp, f'{date} 00:00:00', date))

    def seed_channel(self, scid, node1, node2, funding_block, spending_block, value=1000):
        self.__execute('INSERT INTO Lightning_Channels (ShortChannelID, BlockIndex, TxIndex, OutputIndex, NodeID1, NodeID2) '
                       'VALUES (%s, %s, %s, %s, %s, %s)',
                       (scid, funding_block, 0, 0, node1, node2))
        self.__execute('INSERT INTO Blockchain_Transactions (ShortChannelID, FundingBlockIndex, FundingTxIndex, '
                       'FundingOutputIndex, FundingTxID, FundingScriptHash, Value, SpendingBlockIndex, SpendingTxID, UpdatedDate) '
                       'VALUES (%s, %s, 0, 0, %s, %s, %s, %s, %s, CURDATE())',
                       (scid, funding_block, 'aa' * 32, 'bb' * 32, value, spending_block,
                        '' if spending_block == SENTINEL else 'cc' * 32))

    def seed_cache(self, height, node, channel_count, capacity):
        self.__execute('INSERT INTO _CACHED1_NodeMetrics (BlockHeight, NodeID, ChannelCount, Capacity) '
                       'VALUES (%s, %s, %s, %s)', (height, node, channel_count, capacity))

    def seed_entity(self, node, name):
        self.__execute('INSERT INTO Lightning_Entities (NodeID, EntityName) VALUES (%s, %s)', (node, name))

    def seed_alias(self, node, alias, last_seen='2024-01-01 00:00:00'):
        self.__execute('INSERT INTO Lightning_NodeAliases (NodeID, Alias, firstSeen, lastSeen) VALUES (%s, %s, %s, %s)',
                       (node, alias, last_seen, last_seen))

    def __execute(self, sql, params):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
            conn.commit()

    def heights_structure(self, heights):
        return BlockchainBlockHeightsStructure(
            meta={'type': 't', 'description': 'd', 'updated': 'u', 'xAxis': 'x',
                  'yAxis': 'BlockHeight', 'yAxisSupplyChain': []},
            data={str(h): {'date': '2018-03-01', 'timestamp': 1519862400} for h in heights})








############################################################
# TestDateMaskSelector
############################################################
#
#   test_year_wildcard    — 20XX-03-01 hits every March 1st,
#     lowest block per day, other dates excluded
#   test_month_wildcard   — 20XX-XX-01 hits every month
############################################################

class TestDateMaskSelector(DBFixture):






    ############################################################
    # test_year_wildcard
    ############################################################
    #
    # Proves: the X -> '_' LIKE translation matches March 1st
    # of EVERY year, picks the LOWEST height of each matching
    # day, and ignores neighbouring dates.
    ############################################################

    def test_year_wildcard(self):
        self.seed_block(100, '2018-03-01')
        self.seed_block(101, '2018-03-01')  # same day, higher block — must lose
        self.seed_block(102, '2018-03-02')
        self.seed_block(200, '2018-04-01')
        self.seed_block(300, '2019-03-01')

        result = RawDataSelector().get_first_blocks_of_days_by_date_mask(dateMask='20XX-03-01')
        self.assertEqual(sorted(result.data.keys()), ['100', '300'])
        self.assertEqual(result.data['100'].date, '2018-03-01')






    ############################################################
    # test_month_wildcard
    ############################################################
    #
    # Proves: 20XX-XX-01 selects the first block of every
    # month on record.
    ############################################################

    def test_month_wildcard(self):
        self.seed_block(100, '2018-03-01')
        self.seed_block(200, '2018-04-01')
        self.seed_block(300, '2019-03-01')
        self.seed_block(150, '2018-03-15')  # mid-month — excluded

        result = RawDataSelector().get_first_blocks_of_days_by_date_mask(dateMask='20XX-XX-01')
        self.assertEqual(sorted(result.data.keys(), key=int), ['100', '200', '300'])








############################################################
# TestActivityWindow
############################################################
#
#   test_active_channels_and_double_credit — the funding <=
#     h < spending window and per-endpoint crediting
#   test_close_boundary — a channel closing AT h is inactive
#   test_foreign_key_enforced — init.sql relationships live
############################################################

class TestActivityWindow(DBFixture):






    ############################################################
    # __seed_network
    ############################################################
    #
    # Three channels: A-B open forever (1000 sats), A-C
    # closed at 150 (500), B-C funded later at 200 (700).
    #
    # Used by:
    #   - the activity tests (below)
    ############################################################

    def __seed_network(self):
        self.seed_channel(1, 'A', 'B', funding_block=100, spending_block=SENTINEL, value=1000)
        self.seed_channel(2, 'A', 'C', funding_block=100, spending_block=150, value=500)
        self.seed_channel(3, 'B', 'C', funding_block=200, spending_block=SENTINEL, value=700)






    ############################################################
    # test_active_channels_and_double_credit
    ############################################################
    #
    # Proves, at height 120 (channels 1 and 2 active, 3 not
    # yet funded): each channel credits BOTH endpoints fully,
    # so per-node capacities are A=1500, B=1000, C=500 and the
    # network-wide sum is exactly TWICE the real 1500 sats on
    # chain — the /2 halving downstream in GeneralStats is
    # load-bearing. Channel counts follow the same rule.
    ############################################################

    def test_active_channels_and_double_credit(self):
        self.__seed_network()
        selector = RawDataSelector()

        capacities = {row['NodeID']: int(row['NodeValue']) for row in selector.get_ln_nodes_capacities(120)}
        self.assertEqual(capacities, {'A': 1500, 'B': 1000, 'C': 500})
        self.assertEqual(sum(capacities.values()), 2 * 1500)

        counts = {row['NodeID']: row['ChannelCount'] for row in selector.get_ln_nodes_channel_counts(120)}
        self.assertEqual(counts, {'A': 2, 'B': 1, 'C': 1})






    ############################################################
    # test_close_boundary
    ############################################################
    #
    # Proves: the window is SpendingBlockIndex > h, so a
    # channel spent exactly AT the queried height no longer
    # counts — and one funded exactly AT it already does
    # (FundingBlockIndex <= h).
    ############################################################

    def test_close_boundary(self):
        self.__seed_network()
        capacities = {row['NodeID']: int(row['NodeValue'])
                      for row in RawDataSelector().get_ln_nodes_capacities(150)}
        # channel 2 (closed at 150) is gone; channel 1 remains
        self.assertEqual(capacities, {'A': 1000, 'B': 1000})

        at_200 = {row['NodeID']: int(row['NodeValue'])
                  for row in RawDataSelector().get_ln_nodes_capacities(200)}
        self.assertEqual(at_200, {'A': 1000, 'B': 1700, 'C': 700})  # channel 3 counts at its funding height






    ############################################################
    # test_foreign_key_enforced
    ############################################################
    #
    # Proves: the init.sql relationship is live — an anchor
    # row for a channel that does not exist is rejected by
    # the database itself.
    ############################################################

    def test_foreign_key_enforced(self):
        with self.assertRaises(Exception) as ctx:
            self.seed_channel(99, 'X', 'Y', funding_block=1, spending_block=SENTINEL)
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('DELETE FROM Lightning_Channels WHERE ShortChannelID = 99')
                    cursor.execute('INSERT INTO Blockchain_Transactions (ShortChannelID, FundingBlockIndex, '
                                   'FundingTxIndex, FundingOutputIndex, FundingTxID, FundingScriptHash, Value, '
                                   'SpendingBlockIndex, SpendingTxID, UpdatedDate) '
                                   "VALUES (12345, 1, 0, 0, '', '', 1, 999999999, '', CURDATE())")
        self.assertIn('foreign key', str(ctx.exception).lower())








############################################################
# TestEntityAggregation
############################################################
#
#   test_group_by_entity — nodes of one entity sum together
#   test_missing_entity_row_survives — the COALESCE fallback
#     names an entity-less node after its NodeID
############################################################

class TestEntityAggregation(DBFixture):






    ############################################################
    # test_group_by_entity
    ############################################################
    #
    # Proves: two nodes mapped to the same EntityName merge
    # into one vertex carrying the summed channel count.
    ############################################################

    def test_group_by_entity(self):
        self.seed_block(500, '2018-03-01')
        self.seed_cache(500, 'node1', 2, 100)
        self.seed_cache(500, 'node2', 4, 300)
        self.seed_entity('node1', 'ACME')
        self.seed_entity('node2', 'ACME')

        result = EntityMetricsSelector().get_channel_count_metrics(self.heights_structure([500]))
        vertices = {v.name: v.value for v in result.data['500'].vertices}
        self.assertEqual(vertices, {'ACME': 6})






    ############################################################
    # test_missing_entity_row_survives
    ############################################################
    #
    # Proves: a cached node with NO Lightning_Entities row —
    # possible whenever the entity import lags the cache
    # rebuild — stands as its own entity under its NodeID
    # (COALESCE fallback) instead of the LEFT JOIN's NULL
    # name dying in pydantic validation.
    ############################################################

    def test_missing_entity_row_survives(self):
        self.seed_block(500, '2018-03-01')
        self.seed_cache(500, 'node1', 2, 100)  # deliberately no seed_entity

        result = EntityMetricsSelector().get_channel_count_metrics(self.heights_structure([500]))
        vertices = result.data['500'].vertices
        self.assertEqual(len(vertices), 1)
        self.assertEqual(vertices[0].name, 'node1')
        self.assertEqual(vertices[0].value, 2)








############################################################
# TestLifetimePopulations
############################################################
#
#   test_histogram_population — WHERE semantics live
#   test_average_matches_histogram_population — one
#     population for both statistics, proven with numbers
############################################################

class TestLifetimePopulations(DBFixture):






    ############################################################
    # __seed_lifetimes
    ############################################################
    #
    # Tip at 1000. Three channels: closed 100->200 (lifetime
    # 100), same-block close 100->100 (the contested row),
    # open from 900 (tip-resolved lifetime 100).
    #
    # Used by:
    #   - both tests (below)
    ############################################################

    def __seed_lifetimes(self):
        self.seed_block(1000, '2018-06-01')
        self.seed_channel(1, 'A', 'B', funding_block=100, spending_block=200)
        self.seed_channel(2, 'A', 'C', funding_block=100, spending_block=100)
        self.seed_channel(3, 'B', 'C', funding_block=900, spending_block=SENTINEL)






    ############################################################
    # test_histogram_population
    ############################################################
    #
    # Proves: the histogram's WHERE really drops the
    # same-block close — total_channels is 2, both lifetimes
    # resolve to 100 blocks = day 0 (floor(100/144)).
    ############################################################

    def test_histogram_population(self):
        self.__seed_lifetimes()
        GeneralStats().calculate_channel_lifetime_plot()

        with open('/DATA/GENERATED/General_Stats/Channel_Lifetime/channel_lifetime_plot.json') as f:
            payload = json.load(f)
        self.assertEqual(payload['meta']['total_channels'], 2)
        self.assertEqual(payload['data']['0']['channel_count'], 2)






    ############################################################
    # test_average_matches_histogram_population
    ############################################################
    #
    # Proves: the published average describes the SAME
    # channels as the published histogram — the same-block
    # close is excluded from both, so the mean is exactly 100
    # blocks (that zero-lifetime row used to drag the
    # unfiltered average to 66.67).
    ############################################################

    def test_average_matches_histogram_population(self):
        self.__seed_lifetimes()
        average = GeneralStats().calculate_channel_lifetime_average()
        self.assertAlmostEqual(float(average), 100.0, places=4)








############################################################
# TestEntityNameFixer
############################################################
#
#   test_placeholder_renamed_genuine_hex_survives — the
#     prefix-restricted matcher on real SQL: a NodeID-prefix
#     placeholder gets the freshest alias, a genuine
#     hex-word name keeps it even when an older non-hex
#     alias exists
############################################################

class TestEntityNameFixer(DBFixture):






    ############################################################
    # test_placeholder_renamed_genuine_hex_survives
    ############################################################
    #
    # Proves: only true placeholders — empty names or the
    # exact 20-char NodeID prefix — enter the rename loop. A
    # node whose real, newest alias merely spells a hex word
    # ("decade") keeps that name even though an older non-hex
    # alias ("OldNodeName") would be available to swap in.
    ############################################################

    def test_placeholder_renamed_genuine_hex_survives(self):
        from blnstats.data_transform.entity_clusters import EntityClusters

        placeholder_node = 'aa' * 33
        self.seed_entity(placeholder_node, placeholder_node[:20])
        self.seed_alias(placeholder_node, 'ACINQ')

        hexword_node = 'bb' * 33
        self.seed_entity(hexword_node, 'decade')
        self.seed_alias(hexword_node, 'decade', last_seen='2024-06-01 00:00:00')
        self.seed_alias(hexword_node, 'OldNodeName', last_seen='2020-01-01 00:00:00')

        EntityClusters().fix_entity_hex_names_if_possible()

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT NodeID, EntityName FROM Lightning_Entities')
                names = dict(cursor.fetchall())

        self.assertEqual(names[placeholder_node], 'ACINQ')
        self.assertEqual(names[hexword_node], 'decade')








############################################################
# TestSchemaCompat
############################################################
#
#   test_code_ddl_is_a_noop — the backend's CREATE TABLE IF
#     NOT EXISTS calls coexist with the init.sql schema
############################################################

class TestSchemaCompat(DBFixture):






    ############################################################
    # test_code_ddl_is_a_noop
    ############################################################
    #
    # Proves: create_tables_if_not_exists() runs cleanly
    # against the bootstrapped schema (IF NOT EXISTS no-ops,
    # seeds INSERT IGNORE) — init.sql and the code DDL cannot
    # fight over table shapes on a live system.
    ############################################################

    def test_code_ddl_is_a_noop(self):
        create_tables_if_not_exists()

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'lnstats'")
                self.assertGreaterEqual(cursor.fetchone()[0], 14)








if __name__ == '__main__':
    unittest.main()
