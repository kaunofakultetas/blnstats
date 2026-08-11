############################################################
#  [*] Transform tests — node-metrics merge + entity naming
#
#  The Python halves of the two data transforms, DB stubbed
#  via db_fakes: NodeMetrics.transformForBlockHeight's
#  capacity/channel-count merge (missing side defaults to
#  0) and EntityClusters.fix_entity_hex_names_if_possible's
#  placeholder-name replacement. The expectedFailure test
#  pins the greedy hex matcher: an entity whose REAL alias
#  happens to be all hex characters ("decade", "cafe",
#  "beef" — all valid names) is treated as a placeholder
#  and silently renamed to an older alias.
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
#   test_real_hex_alias_survives (expectedFailure) — the
#     greedy matcher renames genuine hex-word aliases
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
    # test_real_hex_alias_survives
    ############################################################
    #
    # Proves (intended contract): an entity named by a GENUINE
    # alias that merely spells a hex word ("decade" — 6 chars,
    # clearly not a 20-char NodeID prefix) must keep that
    # name. The matcher's REGEXP '^[0-9a-fA-F]+$' treats any
    # hex-only string as a placeholder, so the node's newest
    # alias is silently replaced by an OLDER non-hex one —
    # rewriting entity identity in the published entity
    # metrics.
    ############################################################

    @unittest.expectedFailure
    def test_real_hex_alias_survives(self):
        script = [
            [('node1', 'decade')],  # the node's real, current alias
            ('OldNodeName',),       # an older non-hex alias
        ]
        self.assertEqual(self.__run_fixer(script), [])








if __name__ == '__main__':
    unittest.main()
