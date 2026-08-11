############################################################
#  [*] Transform tests — node-metrics merge + entity naming
#
#  The Python halves of the two data transforms, DB stubbed
#  via db_fakes: NodeMetrics.transformForBlockHeight's
#  capacity/channel-count merge (missing side defaults to
#  0) and EntityClusters.fix_entity_hex_names_if_possible's
#  placeholder-name replacement, now prefix-restricted:
#  only empty names and exact 20-char NodeID prefixes count
#  as placeholders, so a genuine hex-word alias ("decade",
#  "cafe") can never be renamed. The SQL-shape guard lives
#  here (the fakes replay rows regardless of the WHERE);
#  the behavioral proof runs in test_database_selectors.py.
#
#  Used by:
#    - runTests.sh (repo root) — "python3 -m unittest discover"
#      over tests/test_*.py
############################################################


import unittest
from unittest.mock import patch

from blnstats.data_transform import node_metrics as nm_module
from blnstats.data_transform import entity_clusters as ec_module
from blnstats.data_transform.node_metrics import NodeMetrics
from blnstats.data_transform.entity_clusters import EntityClusters
from db_fakes import FakeConn








############################################################
# TestNodeMetricsMerge
############################################################
#
#   test_merge_defaults — the Python full-outer-join: nodes
#     on one side only get 0 on the other; the cache rows
#     replace exactly this height (DELETE first)
############################################################

class TestNodeMetricsMerge(unittest.TestCase):






    ############################################################
    # test_merge_defaults
    ############################################################
    #
    # Proves: a capacity-only node gets ChannelCount 0, a
    # channel-only node gets Capacity 0, a node on both sides
    # keeps both values; the height's old rows are DELETEd
    # before the batched INSERT.
    ############################################################

    def test_merge_defaults(self):
        class FakeSelector:
            def get_ln_nodes_capacities(self, h):
                return [{'NodeID': 'both', 'NodeValue': 500},
                        {'NodeID': 'cap-only', 'NodeValue': 300}]

            def get_ln_nodes_channel_counts(self, h):
                return [{'NodeID': 'both', 'ChannelCount': 4},
                        {'NodeID': 'count-only', 'ChannelCount': 2}]

        executed = []
        metrics = object.__new__(NodeMetrics)
        metrics.raw_data_selector = FakeSelector()

        with patch.object(nm_module, 'get_db_connection', lambda: FakeConn([None, None], executed)):
            metrics.transformForBlockHeight(510000)

        self.assertIn('DELETE', executed[0][0])
        self.assertEqual(executed[0][1], (510000,))

        inserted = sorted(executed[1][1])  # executemany rows
        self.assertEqual(inserted, sorted([
            (510000, 'both', 4, 500),
            (510000, 'cap-only', 0, 300),
            (510000, 'count-only', 2, 0),
        ]))








############################################################
# TestEntityHexNameFixer
############################################################
#
#   test_placeholder_replaced   — 20-hex NodeID prefix gets
#     the freshest non-hex alias
#   test_no_alias_no_update     — nothing usable -> no UPDATE
#   test_fetch_query_is_prefix_restricted — genuine hex-word
#     aliases can never enter the rename loop
############################################################

class TestEntityHexNameFixer(unittest.TestCase):






    ############################################################
    # __run_fixer
    ############################################################
    #
    # Runs the fixer over one scripted entity list and the
    # per-entity alias lookups; returns the UPDATE statements
    # captured (sql, params).
    #
    # Used by:
    #   - every test in this class (below)
    ############################################################

    def __run_fixer(self, script):
        executed = []
        clusters = object.__new__(EntityClusters)
        with patch.object(ec_module, 'get_db_connection', lambda: FakeConn(script, executed)):
            clusters.fix_entity_hex_names_if_possible()
        return [(sql, params) for sql, params in executed if 'UPDATE' in sql]






    ############################################################
    # test_placeholder_replaced
    ############################################################
    #
    # Proves: an entity wearing a 20-hex-char NodeID-prefix
    # placeholder is renamed to its freshest non-hex alias.
    ############################################################

    def test_placeholder_replaced(self):
        script = [
            [('node1', 'abcdef0123456789abcd')],  # SELECT hex-named entities
            ('ACINQ',),                            # freshest usable alias
        ]
        updates = self.__run_fixer(script)
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0][1], ('ACINQ', 'node1'))






    ############################################################
    # test_no_alias_no_update
    ############################################################
    #
    # Proves: a hex-named entity with no usable alias keeps
    # its placeholder — no UPDATE fires.
    ############################################################

    def test_no_alias_no_update(self):
        script = [
            [('node1', 'abcdef0123456789abcd')],
            None,  # alias lookup finds nothing
        ]
        self.assertEqual(self.__run_fixer(script), [])






    ############################################################
    # test_fetch_query_is_prefix_restricted
    ############################################################
    #
    # Proves: the placeholder SELECT only matches empty names
    # or the exact 20-char NodeID prefix — a genuine hex-word
    # alias ("decade", "cafe") can never enter the rename
    # loop. Asserted on the query TEXT because the fakes
    # replay rows regardless of the WHERE; the behavioral
    # proof against real SQL lives in
    # test_database_selectors.py.
    ############################################################

    def test_fetch_query_is_prefix_restricted(self):
        executed = []
        clusters = object.__new__(EntityClusters)
        with patch.object(ec_module, 'get_db_connection', lambda: FakeConn([[]], executed)):
            clusters.fix_entity_hex_names_if_possible()

        fetch_sql = executed[0][0]
        self.assertIn('CHAR_LENGTH(EntityName) = 20', fetch_sql)
        self.assertIn("NodeID LIKE CONCAT(EntityName, '%')", fetch_sql)
        self.assertNotIn('EntityName REGEXP', fetch_sql)








if __name__ == '__main__':
    unittest.main()
