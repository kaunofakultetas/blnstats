############################################################
#  [*] Sync reliability tests — failure paths of the drivers
#
#  Locks the failure-handling contract of the two blockchain
#  sync drivers (data_import/blockchain_blocks.py and
#  blockchain_transactions.py) with DB and Electrum stubbed
#  out: a retry budget exhausted purely by pool-level errors
#  must still raise, an empty Lightning_Channels table must
#  be a clean no-op, and an unconfirmed (mempool) spend must
#  be stored as unspent. These pin the 2026-08 fixes so they
#  cannot regress silently. time.sleep is patched away —
#  the block driver's budget alone is 120 rounds.
#
#  Used by:
#    - runTests.sh (repo root) — "python3 -m unittest discover"
#      over tests/test_*.py
############################################################


import unittest
from unittest.mock import patch

from blnstats.data_import import blockchain_blocks as bb
from blnstats.data_import import blockchain_transactions as bt
from db_fakes import FakeConn








############################################################
# TestBlockSyncReliability
############################################################
#
# sync_blocks() failure paths, on an instance built without
# __init__ (which would want a DB).
#
#   test_tip_fetch_failure_raises      — Electrum down
#   test_pool_exhaustion_raises        — the silent-success
#                                        hole stays closed
############################################################

class TestBlockSyncReliability(unittest.TestCase):






    ############################################################
    # setUp
    ############################################################
    #
    # Bare instance + stub Electrum endpoint; each test patches
    # the module collaborators it needs.
    #
    # Used by:
    #   - the unittest runner, before every test method
    ############################################################

    def setUp(self):
        self.blocks = object.__new__(bb.BlockchainBlocks)
        self.blocks.electrum_host, self.blocks.electrum_port = 'stub', 1






    ############################################################
    # test_tip_fetch_failure_raises
    ############################################################
    #
    # Proves: an unreachable Electrum server fails the sync
    # immediately with BlockSyncError instead of returning.
    ############################################################

    def test_tip_fetch_failure_raises(self):
        with patch.object(bb, 'send_electrum_request', lambda *a, **k: None):
            with self.assertRaises(bb.BlockSyncError):
                self.blocks.sync_blocks()






    ############################################################
    # test_pool_exhaustion_raises
    ############################################################
    #
    # Proves: when every retry round dies at POOL level (the
    # worker itself raises, so no per-height result is ever
    # produced), the leftover heights are still recorded and
    # BlockSyncError carries all of them — the pre-fix code
    # ended such a run reporting success.
    ############################################################

    def test_pool_exhaustion_raises(self):
        def boom(task):
            raise RuntimeError('pool-level failure')

        with patch.object(bb, 'send_electrum_request', lambda *a, **k: {'height': 2}), \
             patch.object(bb, 'retrieve_and_write_blockchain_block', boom), \
             patch.object(bb, 'get_db_connection', lambda: FakeConn([[]], [])), \
             patch('time.sleep', lambda s: None):
            with self.assertRaises(bb.BlockSyncError) as ctx:
                self.blocks.sync_blocks()

        self.assertEqual(len(ctx.exception.failed_blocks), 3)  # heights 0..2








############################################################
# TestTransactionSyncReliability
############################################################
#
# run() and the per-outpoint worker of
# BlockchainTransactions, DB stubbed via db_fakes.
#
#   test_empty_lightning_channels_is_noop — fresh install
#   test_pool_exhaustion_raises           — silent-success
#                                           hole stays closed
#   test_mempool_spend_recorded_as_unspent
#   test_confirmed_spend_recorded
#   test_nonexistent_outpoint_tombstoned  — bogus gossip is
#     quarantined gracefully, not fatal
#   test_young_channel_not_tombstoned     — tip-lag guard
############################################################

class TestTransactionSyncReliability(unittest.TestCase):






    ############################################################
    # setUp
    ############################################################
    #
    # Bare instance + stub Electrum endpoint, as above.
    #
    # Used by:
    #   - the unittest runner, before every test method
    ############################################################

    def setUp(self):
        self.txs = object.__new__(bt.BlockchainTransactions)
        self.txs.electrum_host, self.txs.electrum_port = 'stub', 1






    ############################################################
    # test_empty_lightning_channels_is_noop
    ############################################################
    #
    # Proves: MAX(BlockIndex) = NULL (empty Lightning_Channels)
    # completes as a no-op — the pre-fix code died on
    # None + stepSize before scanning anything.
    ############################################################

    def test_empty_lightning_channels_is_noop(self):
        script = [(None,)]  # MAX() -> NULL; window SELECTs then replay []
        with patch.object(bt, 'get_db_connection', lambda: FakeConn(script, [])):
            self.txs.run(0)  # must simply return






    ############################################################
    # test_pool_exhaustion_raises
    ############################################################
    #
    # Proves: an outpoint whose every retry round dies at POOL
    # level (ThreadPool patched to None, so entering the pool
    # raises before any per-outpoint result exists) still ends
    # in TransactionSyncError naming that outpoint.
    ############################################################

    def test_pool_exhaustion_raises(self):
        script = [(1500,),                     # MAX(BlockIndex)
                  [(1000, 5, 0, 7777)], [], []]  # one pending outpoint, then empty windows
        with patch.object(bt, 'get_db_connection', lambda: FakeConn(script, [])), \
             patch.object(bt, 'ThreadPool', None), \
             patch('time.sleep', lambda s: None):
            with self.assertRaises(bt.TransactionSyncError) as ctx:
                self.txs.run(0)

        self.assertIn((1000, 5, 0, 7777), ctx.exception.failed_transactions)






    ############################################################
    # __run_worker
    ############################################################
    #
    # Shared harness for the worker tests: stubs the private
    # Electrum helpers so only the spend bookkeeping runs, and
    # returns (worker result, INSERT params) for assertions.
    #
    # Used by:
    #   - test_mempool_spend_recorded_as_unspent (below)
    #   - test_confirmed_spend_recorded (below)
    ############################################################

    def __run_worker(self, spending_result):
        executed = []
        self.txs._BlockchainTransactions__get_transaction_details = \
            lambda b, t, o: ('ff' * 32, {'value': 0.5, 'scriptPubKey': {'hex': 'aabbcc'}})
        self.txs._BlockchainTransactions__get_script_hash_from_output = lambda od: 'hash'
        self.txs._BlockchainTransactions__send_electrum_request = lambda *a, **k: []
        self.txs._BlockchainTransactions__get_spending_time_for_output = lambda *a: spending_result

        with patch.object(bt, 'get_db_connection', lambda: FakeConn([None], executed)):
            result = self.txs.retrieveAndWriteLightningBlockchainTxData([1000, 5, 0, 7777])

        return result, executed[0][1]






    ############################################################
    # test_mempool_spend_recorded_as_unspent
    ############################################################
    #
    # Proves: a spend Electrum reports at height 0 (mempool,
    # unconfirmed) is stored as genuinely unspent — sentinel
    # 999999999 AND an empty SpendingTxID — for the weekly
    # recheck to revisit. The pre-fix code wrote the sentinel
    # with a non-empty txid.
    ############################################################

    def test_mempool_spend_recorded_as_unspent(self):
        (info, ok, err), params = self.__run_worker((0, 'aa' * 32))
        self.assertTrue(ok, err)
        self.assertEqual(params[7], '999999999')
        self.assertEqual(params[8], '')






    ############################################################
    # test_confirmed_spend_recorded
    ############################################################
    #
    # Proves: a confirmed spend keeps its real height and txid
    # — the mempool guard must not eat legitimate closures.
    ############################################################

    def test_confirmed_spend_recorded(self):
        (info, ok, err), params = self.__run_worker((800000, 'aa' * 32))
        self.assertTrue(ok, err)
        self.assertEqual(params[7], 800000)
        self.assertEqual(params[8], 'aa' * 32)
        self.assertEqual(params[6], 50000000)  # 0.5 BTC in satoshis






    ############################################################
    # __run_worker_not_found
    ############################################################
    #
    # Worker harness for the TXID_NOT_FOUND path: the funding
    # lookup answers "no such transaction", the Electrum tip
    # is stubbed to tip_height. Returns (result, executed).
    #
    # Used by:
    #   - the two tombstone tests (below)
    ############################################################

    def __run_worker_not_found(self, tip_height):
        executed = []
        txs = object.__new__(bt.BlockchainTransactions)
        txs.electrum_host, txs.electrum_port = 'stub', 1
        txs._BlockchainTransactions__get_transaction_details = lambda b, t, o: (bt.TXID_NOT_FOUND, None)
        txs._BlockchainTransactions__send_electrum_request = lambda *a, **k: {'height': tip_height}

        with patch.object(bt, 'get_db_connection', lambda: FakeConn([None], executed)):
            result = txs.retrieveAndWriteLightningBlockchainTxData([1000, 5, 0, 7777])
        return result, executed






    ############################################################
    # test_nonexistent_outpoint_tombstoned
    ############################################################
    #
    # Proves: a funding position the server DEFINITIVELY says
    # does not exist (bogus gossip past the SegWit floor) is
    # tombstoned — SpendingBlockIndex 0, empty ids, zero
    # value — and reported as SUCCESS, so the sync moves on
    # instead of failing the whole run and never retries this
    # outpoint again.
    ############################################################

    def test_nonexistent_outpoint_tombstoned(self):
        (info, ok, err), executed = self.__run_worker_not_found(tip_height=900000)
        self.assertTrue(ok, err)
        self.assertEqual(len(executed), 1)
        sql, params = executed[0]
        self.assertIn('INSERT INTO Blockchain_Transactions', sql)
        self.assertIn('SpendingBlockIndex = 0', sql)
        self.assertEqual(params, [7777, 1000, 5, 0])






    ############################################################
    # test_young_channel_not_tombstoned
    ############################################################
    #
    # Proves: when the claimed funding block sits within 6
    # blocks of the server tip, "not found" may just be index
    # lag on a freshly confirmed channel — the worker answers
    # retryable failure and writes NOTHING, so a real young
    # channel can never be permanently quarantined by lag.
    ############################################################

    def test_young_channel_not_tombstoned(self):
        (info, ok, err), executed = self.__run_worker_not_found(tip_height=1003)
        self.assertFalse(ok)
        self.assertEqual(executed, [])








if __name__ == '__main__':
    unittest.main()
