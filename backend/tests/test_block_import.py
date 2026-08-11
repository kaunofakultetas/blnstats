############################################################
#  [*] Block import tests — real genesis header + timezones
#
#  Feeds the REAL Bitcoin genesis block header through
#  retrieve_and_write_blockchain_block (Electrum and DB
#  stubbed) and checks every derived field against the
#  publicly known values: the double-sha256 display-order
#  hash and the little-endian timestamp at header offset
#  68. The expectedFailure test pins the timezone bug: the
#  Time/Date columns are rendered with a bare
#  datetime.fromtimestamp(), so the stored strings shift
#  with the container's TZ instead of always being UTC (the
#  test flips TZ to New York and asserts UTC anyway).
#
#  Used by:
#    - runTests.sh (repo root) — "python3 -m unittest discover"
#      over tests/test_*.py
############################################################


import unittest
import os
import time
from unittest.mock import patch

from blnstats.data_import import blockchain_blocks as bb
from db_fakes import FakeConn


# The 80-byte genesis block header and its published facts.
GENESIS_HEADER = ('01000000'
                  + '00' * 32
                  + '3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a'
                  + '29ab5f49' + 'ffff001d' + '1dac2b7c')
GENESIS_HASH = '000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f'
GENESIS_TIMESTAMP = 1231006505  # 2009-01-03 18:15:05 UTC








############################################################
# TestBlockImport
############################################################
#
#   test_genesis_block_fields   — hash + timestamp + UTC time
#   test_time_is_utc_regardless_of_tz (expectedFailure)
############################################################

class TestBlockImport(unittest.TestCase):






    ############################################################
    # setUp / tearDown
    ############################################################
    #
    # Saves and restores the process TZ — the expectedFailure
    # test flips it, and a leak would poison every other
    # datetime in the suite.
    #
    # Used by:
    #   - the unittest runner, around every test method
    ############################################################

    def setUp(self):
        self.saved_tz = os.environ.get('TZ')

    def tearDown(self):
        if self.saved_tz is None:
            os.environ.pop('TZ', None)
        else:
            os.environ['TZ'] = self.saved_tz
        time.tzset()






    ############################################################
    # __import_genesis
    ############################################################
    #
    # Runs the worker on height 0 with Electrum stubbed to the
    # genesis header and returns the captured INSERT params:
    # (height, hash, timestamp, time, date).
    #
    # Used by:
    #   - both tests (below)
    ############################################################

    def __import_genesis(self):
        executed = []
        with patch.object(bb, 'send_electrum_request', lambda *a, **k: GENESIS_HEADER), \
             patch.object(bb, 'get_db_connection', lambda: FakeConn([None], executed)):
            height, ok, err = bb.retrieve_and_write_blockchain_block(
                (0, {'host': 'stub', 'port': 1}))
        self.assertTrue(ok, err)
        return executed[0][1]






    ############################################################
    # test_genesis_block_fields
    ############################################################
    #
    # Proves: the header parse reproduces the publicly known
    # genesis facts — display-order double-sha256 hash and the
    # little-endian timestamp — and (on this UTC container)
    # renders 2009-01-03 18:15:05.
    ############################################################

    def test_genesis_block_fields(self):
        os.environ['TZ'] = 'UTC'
        time.tzset()
        height, block_hash, timestamp, rendered_time, rendered_date = self.__import_genesis()

        self.assertEqual(height, 0)
        self.assertEqual(block_hash, GENESIS_HASH)
        self.assertEqual(timestamp, GENESIS_TIMESTAMP)
        self.assertEqual(rendered_time, '2009-01-03 18:15:05')
        self.assertEqual(rendered_date, '2009-01-03')






    ############################################################
    # test_time_is_utc_regardless_of_tz
    ############################################################
    #
    # Proves (intended contract): the stored Time/Date must be
    # UTC no matter where the container thinks it lives — the
    # Timestamp column is UTC, so a TZ-dependent rendering
    # makes the two columns disagree. Currently a New York TZ
    # stores 13:15:05 for the genesis block.
    ############################################################

    @unittest.expectedFailure
    def test_time_is_utc_regardless_of_tz(self):
        os.environ['TZ'] = 'America/New_York'
        time.tzset()
        _, _, _, rendered_time, rendered_date = self.__import_genesis()

        self.assertEqual(rendered_time, '2009-01-03 18:15:05')
        self.assertEqual(rendered_date, '2009-01-03')








if __name__ == '__main__':
    unittest.main()
