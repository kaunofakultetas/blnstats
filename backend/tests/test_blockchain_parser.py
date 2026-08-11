############################################################
#  [*] Blockchain parser unit tests — the raw byte-walk
#
#  Pins the hand-rolled Bitcoin decoders in
#  data_import/blockchain_transactions.py to synthetic
#  transactions built byte-by-byte in this file: CompactSize
#  varints, legacy and segwit output decoding, the Electrum
#  script-hash convention (sha256, byte-reversed) and the
#  input-section spend check. No DB, no network — the
#  private methods are reached through their name-mangled
#  forms on an instance created without __init__.
#
#  Used by:
#    - backend/runTests.sh — "python3 -m unittest discover"
#      over tests/test_*.py
############################################################


import unittest
import hashlib
from blnstats.data_import.blockchain_transactions import BlockchainTransactions


# One synthetic 1-input / 2-output transaction, assembled from
# labelled pieces so tests can state expectations per field.
# Output 0: 1000 sat, script aabbcc. Output 1: 123456789 sat,
# a P2WPKH-shaped script 0014 + 20 x 22.
TX_VERSION = '02000000'
TX_INPUT = '11' * 32 + '00000000' + '00' + 'ffffffff'
TX_OUTPUTS = ('02'
              + 'e803000000000000' + '03' + 'aabbcc'
              + '15cd5b0700000000' + '16' + '0014' + '22' * 20)
TX_LOCKTIME = '00000000'

LEGACY_TX = TX_VERSION + '01' + TX_INPUT + TX_OUTPUTS + TX_LOCKTIME

# Same transaction in segwit encoding: marker 00 + flag 01
# after the version, one dummy witness item before locktime
# (the parser must never reach it).
SEGWIT_TX = TX_VERSION + '0001' + '01' + TX_INPUT + TX_OUTPUTS + '0101ff' + TX_LOCKTIME








############################################################
# TestBlockchainParser
############################################################
#
# All tests share one uninitialized BlockchainTransactions
# (object.__new__ skips __init__, which would want a DB) and
# reach the private decoders via name mangling.
#
#   test_read_varint_*            — CompactSize decoder
#   test_parse_legacy/segwit_*    — output byte-walk
#   test_parse_out_of_range       — bounds check -> None
#   test_script_hash              — Electrum hash convention
#   test_spends_output_*          — input-section spend scan
############################################################

class TestBlockchainParser(unittest.TestCase):






    ############################################################
    # setUp
    ############################################################
    #
    # Instance without __init__ — the decoders are pure and
    # never touch self beyond method dispatch.
    #
    # Used by:
    #   - the unittest runner, before every test method
    ############################################################

    def setUp(self):
        self.txs = object.__new__(BlockchainTransactions)
        self.read_varint = self.txs._BlockchainTransactions__read_varint
        self.parse = self.txs._BlockchainTransactions__parse_raw_transaction
        self.script_hash = self.txs._BlockchainTransactions__get_script_hash_from_output
        self.spends = self.txs._BlockchainTransactions__transaction_spends_output






    ############################################################
    # test_read_varint_single_byte
    ############################################################
    #
    # Proves: a first byte below 0xfd IS the value, and the
    # offset advances by exactly one — also from a nonzero
    # start offset.
    ############################################################

    def test_read_varint_single_byte(self):
        self.assertEqual(self.read_varint(b'\x2a', 0), (42, 1))
        self.assertEqual(self.read_varint(b'\x00\xfc', 1), (252, 2))






    ############################################################
    # test_read_varint_prefixed
    ############################################################
    #
    # Proves: 0xfd/0xfe/0xff prefix a 2/4/8-byte little-endian
    # integer and the offset lands just past it.
    ############################################################

    def test_read_varint_prefixed(self):
        self.assertEqual(self.read_varint(b'\xfd\x00\x01', 0), (256, 3))
        self.assertEqual(self.read_varint(b'\xfe\x78\x56\x34\x12', 0), (0x12345678, 5))
        self.assertEqual(self.read_varint(b'\xff' + (2 ** 40).to_bytes(8, 'little'), 0), (2 ** 40, 9))






    ############################################################
    # test_parse_legacy_outputs
    ############################################################
    #
    # Proves: both outputs of the legacy transaction decode to
    # the expected float-BTC value and scriptPubKey hex.
    ############################################################

    def test_parse_legacy_outputs(self):
        out0 = self.parse(LEGACY_TX, 0)
        self.assertEqual(out0['value'], 0.00001)
        self.assertEqual(out0['scriptPubKey']['hex'], 'aabbcc')

        out1 = self.parse(LEGACY_TX, 1)
        self.assertEqual(out1['value'], 1.23456789)
        self.assertEqual(out1['scriptPubKey']['hex'], '0014' + '22' * 20)






    ############################################################
    # test_parse_segwit_outputs
    ############################################################
    #
    # Proves: the segwit marker/flag is hopped and the output
    # section decodes identically to the legacy encoding.
    ############################################################

    def test_parse_segwit_outputs(self):
        out1 = self.parse(SEGWIT_TX, 1)
        self.assertEqual(out1['value'], 1.23456789)
        self.assertEqual(out1['scriptPubKey']['hex'], '0014' + '22' * 20)






    ############################################################
    # test_parse_out_of_range
    ############################################################
    #
    # Proves: an output index past the end returns None (the
    # caller's retryable-failure signal), never an exception.
    ############################################################

    def test_parse_out_of_range(self):
        self.assertIsNone(self.parse(LEGACY_TX, 2))






    ############################################################
    # test_script_hash
    ############################################################
    #
    # Proves: the Electrum script hash is sha256 of the raw
    # script bytes, BYTE-REVERSED, hex-encoded — the reversal
    # is the part a refactor would silently drop.
    ############################################################

    def test_script_hash(self):
        script_hex = '0014' + '22' * 20
        expected = hashlib.sha256(bytes.fromhex(script_hex)).digest()[::-1].hex()
        got = self.script_hash({'scriptPubKey': {'hex': script_hex}})
        self.assertEqual(got, expected)
        self.assertNotEqual(got, hashlib.sha256(bytes.fromhex(script_hex)).hexdigest())






    ############################################################
    # test_spends_output_match
    ############################################################
    #
    # Proves: a spender whose input carries the target outpoint
    # is detected — the input's wire-order prev-txid must be
    # byte-reversed to match the display-order target.
    ############################################################

    def test_spends_output_match(self):
        wire_txid = bytes(range(32))
        display_txid = wire_txid[::-1].hex()
        spender = ('01000000' + '01'
                   + wire_txid.hex() + '03000000' + '00' + 'ffffffff'
                   + '01' + '00' * 8 + '00' + '00000000')

        self.assertTrue(self.spends(spender, display_txid, 3))
        self.assertFalse(self.spends(spender, display_txid, 2))
        self.assertFalse(self.spends(spender, wire_txid.hex(), 3))






    ############################################################
    # test_spends_output_corrupt_is_false
    ############################################################
    #
    # Proves: unparseable hex answers False ("does not spend"),
    # never raises — the documented err-toward-open behavior.
    ############################################################

    def test_spends_output_corrupt_is_false(self):
        self.assertFalse(self.spends('zz-not-hex', '00' * 32, 0))
        self.assertFalse(self.spends('0100', '00' * 32, 0))








if __name__ == '__main__':
    unittest.main()
