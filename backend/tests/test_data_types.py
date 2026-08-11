############################################################
#  [*] Data-structure tests — the pipeline's common currency
#
#  Pins the pydantic structures in blnstats/data_types.py:
#  the all-fields-required MetaDataStructure contract, the
#  str-to-int timestamp coercion the selectors rely on, and
#  the save_to_file / save_to_csv output formats (JSON shape,
#  CSV header and rows, the divideValueBy formatting split).
#  Files land in a TemporaryDirectory — nothing touches
#  /DATA.
#
#  Used by:
#    - runTests.sh (repo root) — "python3 -m unittest discover"
#      over tests/test_*.py
############################################################


import unittest
import json
import os
import tempfile
from pydantic import ValidationError

from blnstats.data_types import (
    MetaDataStructure,
    BlockchainBlockHeightsStructure,
    VerticesAspectDataStructure,
)


# Every structure carries this envelope; individual tests
# override nothing — the values are opaque to the code.
META = {
    'type': 'test',
    'description': 'unit test structure',
    'updated': '2026-08-11',
    'xAxis': 'Date',
    'yAxis': 'Value',
    'yAxisSupplyChain': ['Value'],
}








############################################################
# TestMetaDataStructure
############################################################
#
#   test_all_fields_required — the missing-'updated' case is
#     exactly what makes raw_data_selector's withMeta=True
#     path blow up today
############################################################

class TestMetaDataStructure(unittest.TestCase):






    ############################################################
    # test_all_fields_required
    ############################################################
    #
    # Proves: a complete envelope validates; dropping ANY
    # field (here 'updated') raises ValidationError.
    ############################################################

    def test_all_fields_required(self):
        MetaDataStructure(**META)

        incomplete = {k: v for k, v in META.items() if k != 'updated'}
        with self.assertRaises(ValidationError):
            MetaDataStructure(**incomplete)








############################################################
# TestBlockchainBlockHeightsStructure
############################################################
#
#   test_str_timestamp_coerced — the selectors pass numeric
#     strings; pydantic must keep turning them into ints
#   test_save_to_file_shape    — the meta+data JSON envelope
############################################################

class TestBlockchainBlockHeightsStructure(unittest.TestCase):






    ############################################################
    # test_str_timestamp_coerced
    ############################################################
    #
    # Proves: a "1514764800" string timestamp comes out as the
    # int 1514764800 — the selector feeds strings and every
    # consumer does arithmetic on the result.
    ############################################################

    def test_str_timestamp_coerced(self):
        s = BlockchainBlockHeightsStructure(
            meta=META,
            data={'510123': {'date': '2018-01-01', 'timestamp': '1514764800'}},
        )
        self.assertEqual(s.data['510123'].timestamp, 1514764800)






    ############################################################
    # test_save_to_file_shape
    ############################################################
    #
    # Proves: save_to_file writes the { meta: {...}, data:
    # {...} } envelope as valid JSON, creating parent
    # directories on the way.
    ############################################################

    def test_save_to_file_shape(self):
        s = BlockchainBlockHeightsStructure(
            meta=META,
            data={'510123': {'date': '2018-01-01', 'timestamp': 1514764800}},
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'sub', 'dir', 'blocks.json')
            s.save_to_file(path)
            with open(path) as f:
                obj = json.load(f)

        self.assertEqual(obj['meta']['updated'], '2026-08-11')
        self.assertEqual(obj['data']['510123']['timestamp'], 1514764800)








############################################################
# TestVerticesAspectDataStructure
############################################################
#
#   test_save_to_csv_raw       — divideValueBy=1.0 keeps raw
#     int values
#   test_save_to_csv_divided   — any other divisor yields
#     8-decimal strings
############################################################

class TestVerticesAspectDataStructure(unittest.TestCase):






    ############################################################
    # __build
    ############################################################
    #
    # One block height with two vertices — enough to check
    # ordering, values and the per-row date column.
    #
    # Used by:
    #   - both CSV tests (below)
    ############################################################

    def __build(self):
        return VerticesAspectDataStructure(
            meta=META,
            data={'505000': {
                'date': '2018-01-01',
                'timestamp': 1514764800,
                'vertices': [
                    {'name': 'node-a', 'value': 12345678},
                    {'name': 'node-b', 'value': 100},
                ],
            }},
        )






    ############################################################
    # test_save_to_csv_raw
    ############################################################
    #
    # Proves: the CSV carries the name,value,date header and
    # one row per vertex with the raw integer value when
    # divideValueBy stays 1.0.
    ############################################################

    def test_save_to_csv_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'vertices.csv')
            self.__build().save_to_csv(path)
            with open(path) as f:
                lines = f.read().splitlines()

        self.assertEqual(lines[0], 'name,value,date')
        self.assertEqual(lines[1], 'node-a,12345678,2018-01-01')
        self.assertEqual(lines[2], 'node-b,100,2018-01-01')






    ############################################################
    # test_save_to_csv_divided
    ############################################################
    #
    # Proves: divideValueBy != 1.0 renders values as 8-decimal
    # strings (satoshi -> BTC style).
    ############################################################

    def test_save_to_csv_divided(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'vertices.csv')
            self.__build().save_to_csv(path, divideValueBy=100000000)
            with open(path) as f:
                lines = f.read().splitlines()

        self.assertEqual(lines[1], 'node-a,0.12345678,2018-01-01')
        self.assertEqual(lines[2], 'node-b,0.00000100,2018-01-01')








if __name__ == '__main__':
    unittest.main()
