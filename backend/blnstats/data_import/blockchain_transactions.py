############################################################
#  [*] Blockchain transactions — LN funding outputs on-chain
#
#  Anchors Lightning channels to the Bitcoin chain over a
#  raw Electrum TCP connection: for every channel outpoint
#  in Lightning_Channels it resolves the funding txid and
#  value, hand-parses the raw transaction bytes, and scans
#  the output's script-hash history to find the spending
#  (channel-closing) transaction, if any. Results are
#  upserted into Blockchain_Transactions.
#
#  Neighbours: Lightning_Channels rows come in from the
#  gossip importers (lnd_dbreader.py, ln_research.py);
#  Blockchain_Transactions flows on to
#  database/raw_data_selector.py and
#  calculations/general_stats.py (capacity and channel-life
#  queries). The only driver is synchronizeBlockchain() in
#  blnstats/__init__.py.
#
#  Wire-format ground rules used throughout:
#    - Electrum speaks newline-delimited JSON-RPC over a
#      plain TCP socket (no TLS)
#    - integers in raw transactions are little-endian;
#      counts use Bitcoin's CompactSize varint encoding
#    - segwit txs are detected by the 0x00 0x01 marker/flag
#      pair after the version field
#    - txids are compared in DISPLAY order (byte-reversed
#      from wire order)
#    - SpendingBlockIndex 999999999 is the sentinel for
#      "funding output not spent yet"
############################################################


import socket
import json
import hashlib
import time
import logging
from decimal import Decimal
from multiprocessing.dummy import Pool as ThreadPool
from ..database.utils import get_db_connection
from dataclasses import dataclass
from typing import List, Dict, Tuple

# NOTE: `dataclass` and `List` are imported above but never
# used anywhere in this module — dead imports.

# basicConfig at import time: whichever blnstats module is
# imported first wins the root-logger configuration.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gates the very chatty per-byte DEBUG prints in the raw-tx
# parsing helpers — flip on only when debugging the parser.
DEBUG_ENABLED = False








############################################################
# TransactionSyncError
############################################################
#
# Terminal failure signal of a transaction sync: raised once
# at the end of BlockchainTransactions.run() when outpoints
# are still failing after every retry round. Carries the
# per-outpoint error map, keyed (blockIndex, txIndex,
# outputIndex, shortChannelID), so the log shows exactly
# which channels never resolved.
#
# Used by:
#   - BlockchainTransactions.run (below) — the only raise
#     site; nothing catches it upstream, so it aborts the
#     --sync-blockchain CLI run / synchronize_blockchain
#     workflow task
############################################################

class TransactionSyncError(Exception):






    ############################################################
    # __init__
    ############################################################
    #
    # Builds the message eagerly so a bare str(exc) in the
    # workflow log already names every failed outpoint key.
    #
    # Used by:
    #   - BlockchainTransactions.run (below)
    ############################################################

    def __init__(self, failed_transactions: Dict[Tuple[int, int, int, int], str], total_transactions_attempted: int):
        self.failed_transactions = failed_transactions
        self.total_transactions_attempted = total_transactions_attempted
        self.failed_count = len(failed_transactions)
        
        message = (f"Failed to sync {self.failed_count} out of {total_transactions_attempted} transactions. "
                  f"Failed transactions: {list(failed_transactions.keys())}")
        super().__init__(message)








############################################################
# DecimalEncoder
############################################################
#
# json.JSONEncoder that serialises Decimal as a string
# instead of raising TypeError.
#
# Used by:
#   - BlockchainTransactions.retrieveAndWriteLightningBlockchainTxData
#     (below) — inside a dumps/loads round-trip of the parsed
#     output details. NOTE: __parse_raw_transaction only ever
#     emits plain floats/strs, so the Decimal branch never
#     fires there — the round-trip is a leftover from a
#     verbose-RPC data source and is effectively a no-op.
############################################################

class DecimalEncoder(json.JSONEncoder):






    ############################################################
    # default
    ############################################################
    #
    # Stringifies Decimal; every other type falls through to
    # the stock encoder (which raises for unknown types).
    #
    # Used by:
    #   - json.dumps(..., cls=DecimalEncoder) in
    #     retrieveAndWriteLightningBlockchainTxData (below)
    ############################################################

    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)








############################################################
# BlockchainTransactions
############################################################
#
# Importer that anchors Lightning channels to the Bitcoin
# chain. For every channel funding outpoint recorded in
# Lightning_Channels it resolves the funding txid, output
# value and script hash via Electrum, determines whether the
# funding output was already spent (= channel closed), and
# upserts the result into Blockchain_Transactions.
#
# Method map (details live on each method):
#   __createTablesIfNotExist         — DDL
#   __send_electrum_request          — raw TCP JSON-RPC call
#   __parse_raw_transaction          — byte-walk one output
#   __read_varint                    — CompactSize decoder
#   __get_transaction_details        — txid + output for pos
#   __get_script_hash_from_output    — Electrum script hash
#   __get_spending_time_for_output   — find the spending tx
#   __transaction_spends_output      — input-section scan
#   retrieveAndWriteLightningBlockchainTxData — one outpoint
#   run                              — batch driver
#
# Used by:
#   - synchronizeBlockchain() in blnstats/__init__.py — the
#     only constructor call; reached from main.py
#     --sync-blockchain and the synchronize_blockchain task
#     in workflows.py
############################################################

class BlockchainTransactions:






    ############################################################
    # __init__
    ############################################################
    #
    # Stores the Electrum endpoint and makes sure the target
    # table exists. No connection to Electrum is opened here —
    # every request later dials a fresh socket.
    #
    # Used by:
    #   - synchronizeBlockchain() in blnstats/__init__.py
    ############################################################

    def __init__(self, electrum_host: str, electrum_port: int):
        self.electrum_host = electrum_host
        self.electrum_port = electrum_port

        with get_db_connection() as db_conn:
            with db_conn.cursor() as db_cursor:
                self.__createTablesIfNotExist(db_cursor)






    ############################################################
    # __createTablesIfNotExist
    ############################################################
    #
    # DDL for Blockchain_Transactions: one row per channel
    # funding output, keyed by ShortChannelID, with
    # SpendingBlockIndex 999999999 meaning "not spent yet".
    # NOTE: database/utils.py create_tables_if_not_exists()
    # carries a second copy of this DDL with an EXTRA covering
    # index (idx_funding_spending_value_covering) — whichever
    # runs first wins, because CREATE TABLE IF NOT EXISTS
    # never alters an existing table.
    #
    # Used by:
    #   - __init__ (above)
    ############################################################

    def __createTablesIfNotExist(self, db_cursor):
        db_cursor.execute('''
            CREATE TABLE IF NOT EXISTS `Blockchain_Transactions` (
                `ShortChannelID` BIGINT UNSIGNED NOT NULL UNIQUE,
                `FundingBlockIndex` INT UNSIGNED NOT NULL,
                `FundingTxIndex` INT UNSIGNED NOT NULL,
                `FundingOutputIndex` SMALLINT UNSIGNED NOT NULL,
                `FundingTxID` CHAR(64) NOT NULL,
                `FundingScriptHash` CHAR(64) NOT NULL,
                `Value` BIGINT UNSIGNED NOT NULL,
                `SpendingBlockIndex` INT UNSIGNED NOT NULL,
                `SpendingTxID` CHAR(64) NOT NULL,
                `UpdatedDate` DATE NOT NULL,
                PRIMARY KEY (`ShortChannelID`),
                INDEX `idx_Funding_SpendingBlockIndex` (`FundingBlockIndex`, `SpendingBlockIndex`),
                INDEX `idx_Value` (`Value`)
            );
        ''')






    ############################################################
    # __send_electrum_request
    ############################################################
    #
    # One Electrum JSON-RPC call over a fresh plain TCP
    # socket (newline-delimited JSON, no TLS). Reads until the
    # first chunk containing a LF — safe because Electrum
    # answers a single request with a single LF-terminated
    # line. Returns the 'result' payload, or None on any
    # network/protocol error (errors are logged, never
    # raised). NOTE: the socket is only closed on the happy
    # path — an exception mid-request leaks the descriptor
    # until the GC collects it.
    #
    # Used by:
    #   - __get_transaction_details (below)
    #   - __get_spending_time_for_output (below)
    #   - retrieveAndWriteLightningBlockchainTxData (below)
    ############################################################

    def __send_electrum_request(self, server_ip: str, server_port: int, method: str, params: list):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((server_ip, server_port))

            request = {
                "id": 0,
                "method": method,
                "params": params
            }
            request_str = json.dumps(request) + '\n'
            s.sendall(request_str.encode())

            chunks = []
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
                if b'\n' in chunk:
                    break
            s.close()

            # one LF-terminated JSON line is the whole reply
            response = b''.join(chunks).decode()
            response_json = json.loads(response)

            # a JSON-RPC error object means the call failed even
            # though the socket read succeeded — log and swallow
            if isinstance(response_json, dict) and 'error' in response_json and response_json['error']:
                error_info = response_json['error']
                if isinstance(error_info, dict) and 'message' in error_info:
                    logger.error(f"Error from Electrum server for method {method}: {error_info['message']}")
                else:
                    logger.error(f"Error from Electrum server for method {method}: {error_info}")
                return None

            return response_json.get('result') if isinstance(response_json, dict) else response_json
            
        except Exception as e:
            logger.error(f"Network error calling Electrum method {method}: {e}")
            return None






    ############################################################
    # __parse_raw_transaction
    ############################################################
    #
    # Hand-rolled decoder for ONE output of a raw Bitcoin
    # transaction, legacy or segwit: version(4, LE) ->
    # [marker+flag] -> varint input count -> inputs -> varint
    # output count -> outputs. Only the requested output is
    # decoded; witness data and locktime are never touched.
    # Returns {'value': <float BTC>, 'scriptPubKey': {'hex':
    # ...}} — mimicking bitcoind's verbose shape, which
    # Electrum cannot serve — or None on any parse problem.
    #
    # Used by:
    #   - __get_transaction_details (below)
    ############################################################

    def __parse_raw_transaction(self, raw_tx_hex: str, output_index: int):
        try:
            # STEP 1: hex to bytes; a transaction opens with a
            # 4-byte little-endian version field
            # ================================================
            if DEBUG_ENABLED:
                print(f"DEBUG: Parsing transaction hex (length: {len(raw_tx_hex)}) for output index {output_index}")

            tx_bytes = bytes.fromhex(raw_tx_hex)
            offset = 0

            version = int.from_bytes(tx_bytes[offset:offset + 4], 'little')
            if DEBUG_ENABLED:
                print(f"DEBUG: Transaction version: {version}")
            offset += 4


            # STEP 2: segwit marker (0x00) + flag (0x01) right
            # after the version — unambiguous, because a legacy
            # tx would put its input count here and zero inputs
            # is invalid
            # =================================================
            is_segwit = False  # NOTE: assigned but never read again — dead flag
            if tx_bytes[offset] == 0x00 and tx_bytes[offset + 1] == 0x01:
                if DEBUG_ENABLED:
                    print("DEBUG: SegWit transaction detected")
                is_segwit = True
                offset += 2  # only marker+flag; the rest reads like legacy


            # STEP 3: skip the input section — 32-byte prev txid
            # + 4-byte vout + varint script + 4-byte sequence per
            # input; input contents are irrelevant here
            # ===================================================
            input_count, offset = self.__read_varint(tx_bytes, offset)
            if DEBUG_ENABLED:
                print(f"DEBUG: Input count: {input_count}")

            for i in range(input_count):
                if DEBUG_ENABLED:
                    print(f"DEBUG: Processing input {i}")
                offset += 32  # prev txid
                offset += 4   # prev vout
                script_length, offset = self.__read_varint(tx_bytes, offset)
                if DEBUG_ENABLED:
                    print(f"DEBUG: Input {i} script length: {script_length}")
                offset += script_length
                offset += 4   # sequence


            # STEP 4: output count, then bounds-check the
            # requested index before walking
            # ===========================================
            output_count, offset = self.__read_varint(tx_bytes, offset)
            if DEBUG_ENABLED:
                print(f"DEBUG: Output count: {output_count}, requested index: {output_index}")
            
            if output_index >= output_count:
                print(f"ERROR: Output index {output_index} out of range (transaction has {output_count} outputs)")
                return None


            # STEP 5: hop over the outputs before the target —
            # 8-byte little-endian value + varint scriptPubKey
            # each
            # ================================================
            for i in range(output_index):
                if DEBUG_ENABLED:
                    print(f"DEBUG: Skipping output {i}")
                offset += 8
                script_length, offset = self.__read_varint(tx_bytes, offset)
                if DEBUG_ENABLED:
                    print(f"DEBUG: Output {i} script length: {script_length}")
                offset += script_length

            if DEBUG_ENABLED:
                print(f"DEBUG: Reading target output {output_index} at offset {offset}")


            # STEP 6: decode the target output. Witness data and
            # locktime sit AFTER the outputs, so they are never
            # reached — the output section parses identically in
            # legacy and segwit encodings.
            # ==================================================
            value_bytes = tx_bytes[offset:offset + 8]
            value_satoshis = int.from_bytes(value_bytes, 'little')
            if DEBUG_ENABLED:
                print(f"DEBUG: Output value: {value_satoshis} satoshis")
            offset += 8

            script_length, offset = self.__read_varint(tx_bytes, offset)
            if DEBUG_ENABLED:
                print(f"DEBUG: Target output script length: {script_length}")
            script_bytes = tx_bytes[offset:offset + script_length]
            script_hex = script_bytes.hex()
            if DEBUG_ENABLED:
                print(f"DEBUG: Script hex: {script_hex}")

            # the exact satoshi count degrades to a float BTC
            # amount here; the caller converts back via
            # Decimal(str(...)) — fine for real channel sizes,
            # but lossy by construction
            return {
                'value': value_satoshis / 100000000,  # float BTC
                'scriptPubKey': {'hex': script_hex}
            }

        except Exception as e:
            print(f"Error parsing raw transaction: {e}")
            if DEBUG_ENABLED:
                import traceback
                traceback.print_exc()
            return None






    ############################################################
    # __read_varint
    ############################################################
    #
    # Bitcoin CompactSize decoder: a first byte below 0xfd IS
    # the value; 0xfd/0xfe/0xff prefix a 2/4/8-byte
    # little-endian integer. Returns (value, new_offset). All
    # 256 first-byte cases are covered, so the implicit None
    # fall-through is unreachable.
    #
    # Used by:
    #   - __parse_raw_transaction (above)
    #   - __transaction_spends_output (below)
    ############################################################

    def __read_varint(self, data: bytes, offset: int):
        first_byte = data[offset]

        if first_byte < 0xfd:
            return first_byte, offset + 1
        elif first_byte == 0xfd:
            return int.from_bytes(data[offset + 1:offset + 3], 'little'), offset + 3
        elif first_byte == 0xfe:
            return int.from_bytes(data[offset + 1:offset + 5], 'little'), offset + 5
        elif first_byte == 0xff:
            return int.from_bytes(data[offset + 1:offset + 9], 'little'), offset + 9






    ############################################################
    # __get_transaction_details
    ############################################################
    #
    # (block height, tx position) -> (txid, decoded output).
    # Two Electrum round-trips: transaction.id_from_pos for
    # the txid, then transaction.get for the raw hex, decoded
    # locally by __parse_raw_transaction. Returns (None, None)
    # on any failure so the caller treats the outpoint as
    # retryable.
    #
    # Used by:
    #   - retrieveAndWriteLightningBlockchainTxData (below)
    ############################################################

    def __get_transaction_details(self, block_height: int, tx_index: int, output_index: int):
        try:
            # STEP 1: resolve (height, position) to a txid
            # ============================================
            tx_id_raw = self.__send_electrum_request(self.electrum_host, self.electrum_port, "blockchain.transaction.id_from_pos", [block_height, tx_index])

            if not tx_id_raw:
                return None, None

            # some servers hand the txid back double-JSON-encoded
            # ('"abc..."') — peel the quoting layers until bare
            tx_id = tx_id_raw
            while isinstance(tx_id, str) and tx_id.startswith('"') and tx_id.endswith('"'):
                tx_id = json.loads(tx_id)


            # STEP 2: fetch the raw hex — Electrum has no verbose
            # mode, so all decoding happens locally
            # ===================================================
            raw_tx_hex = self.__send_electrum_request(self.electrum_host, self.electrum_port, "blockchain.transaction.get", [tx_id])

            if not raw_tx_hex:
                return None, None


            # STEP 3: decode just the requested output
            # ========================================
            output_details = self.__parse_raw_transaction(raw_tx_hex, output_index)

            if not output_details:
                print(f"Failed to parse transaction {tx_id} at block {block_height}, tx {tx_index}, output {output_index}")
                return None, None

            return tx_id, output_details

        except Exception as e:
            print(f"An error occurred in __get_transaction_details: {e}")
            return None, None






    ############################################################
    # __get_script_hash_from_output
    ############################################################
    #
    # scriptPubKey hex -> Electrum script hash: sha256 of the
    # raw script bytes, byte-REVERSED, hex-encoded. Electrum
    # indexes outputs by this hash rather than by address, and
    # the reversal is part of its protocol definition.
    #
    # Used by:
    #   - retrieveAndWriteLightningBlockchainTxData (below) —
    #     feeds blockchain.scripthash.get_history
    ############################################################

    def __get_script_hash_from_output(self, output_details):
        script_pub_key = output_details['scriptPubKey']['hex']
        script_pub_key_bytes = bytes.fromhex(script_pub_key)
        sha256_hash = hashlib.sha256(script_pub_key_bytes).digest()
        reversed_hash = sha256_hash[::-1]
        script_hash = reversed_hash.hex()
        return script_hash






    ############################################################
    # __get_spending_time_for_output
    ############################################################
    #
    # Walks the script-hash history of the funding output and
    # fetches every candidate transaction to see whether one
    # of its inputs consumes tx_id_to_check:output_index. On a
    # hit returns (height, txid); if nothing in the history
    # spends it, (None, None). Up to 3 failed fetches merely
    # skip a candidate; the 3rd raises, so the caller marks
    # the outpoint failed instead of recording a false
    # "unspent" (a skipped candidate could BE the spend).
    #
    # GOTCHA: Electrum reports height 0 (or -1) for mempool
    # transactions, so a mempool spend comes back as height 0
    # — falsy for the caller; see the BUG note on
    # retrieveAndWriteLightningBlockchainTxData.
    #
    # Used by:
    #   - retrieveAndWriteLightningBlockchainTxData (below)
    ############################################################

    def __get_spending_time_for_output(self, tx_id_to_check, output_index_to_check, script_hash_history):
        if DEBUG_ENABLED:
            logger.debug(f"Checking spending for {tx_id_to_check}:{output_index_to_check}")
            logger.debug(f"Script hash history has {len(script_hash_history) if script_hash_history else 0} entries")
        
        network_errors = 0
        max_network_errors = 3  # every skipped candidate could BE the spend — cap the risk

        for entry in script_hash_history:
            tx_hash = entry['tx_hash']
            
            if DEBUG_ENABLED:
                logger.debug(f"Checking transaction {tx_hash} at height {entry['height']}")
            
            # raw hex only — Electrum has no verbose mode, so the
            # spend check is a local byte-walk
            raw_tx_hex = self.__send_electrum_request(self.electrum_host, self.electrum_port, "blockchain.transaction.get", [tx_hash])

            if not raw_tx_hex:
                network_errors += 1
                logger.warning(f"Could not get raw hex for {tx_hash} (error {network_errors}/{max_network_errors})")
                
                if network_errors >= max_network_errors:
                    raise Exception(f"Too many network errors ({network_errors}) while checking spending transactions")
                continue

            if self.__transaction_spends_output(raw_tx_hex, tx_id_to_check, output_index_to_check):
                if DEBUG_ENABLED:
                    logger.debug("Found spending transaction!")
                return entry['height'], tx_hash
        
        if DEBUG_ENABLED:
            logger.debug("No spending transaction found")
        return None, None






    ############################################################
    # __transaction_spends_output
    ############################################################
    #
    # Answers "does this raw transaction spend
    # target_txid:target_output_index?" by walking only the
    # input section. Each input's 32-byte prev-txid is
    # byte-reversed to display order before comparing, because
    # target_txid arrives in display order. Returns False on
    # ANY parse error — a corrupt fetch is indistinguishable
    # from "does not spend it", which errs toward recording a
    # channel as still open.
    #
    # Used by:
    #   - __get_spending_time_for_output (above)
    ############################################################

    def __transaction_spends_output(self, raw_tx_hex: str, target_txid: str, target_output_index: int):
        try:
            # STEP 1: skip the version, hop the segwit
            # marker/flag if present (same detection trick as in
            # __parse_raw_transaction)
            # ==================================================
            tx_bytes = bytes.fromhex(raw_tx_hex)
            offset = 0

            offset += 4  # version

            if tx_bytes[offset] == 0x00 and tx_bytes[offset + 1] == 0x01:
                offset += 2  # marker + flag


            # STEP 2: walk the inputs, comparing each outpoint
            # against the target; outputs are never reached
            # ================================================
            input_count, offset = self.__read_varint(tx_bytes, offset)

            if DEBUG_ENABLED:
                print(f"DEBUG: Checking {input_count} inputs in spending candidate")

            for i in range(input_count):
                prev_hash_bytes = tx_bytes[offset:offset + 32]
                prev_hash = prev_hash_bytes[::-1].hex()  # wire order -> display order, to match target_txid
                offset += 32

                prev_index_bytes = tx_bytes[offset:offset + 4]
                prev_index = int.from_bytes(prev_index_bytes, 'little')
                offset += 4

                if DEBUG_ENABLED:
                    print(f"DEBUG: Input {i}: {prev_hash}:{prev_index}")
                    print(f"DEBUG: Target: {target_txid}:{target_output_index}")

                if prev_hash == target_txid and prev_index == target_output_index:
                    if DEBUG_ENABLED:
                        print(f"DEBUG: MATCH FOUND!")
                    return True

                script_length, offset = self.__read_varint(tx_bytes, offset)
                offset += script_length

                offset += 4  # sequence

            return False

        except Exception as e:
            print(f"Error checking if transaction spends output: {e}")
            return False






    ############################################################
    # retrieveAndWriteLightningBlockchainTxData
    ############################################################
    #
    # Worker for ONE channel outpoint, run 10-at-a-time via
    # ThreadPool in run(). data is [blockIndex, txIndex,
    # outputIndex, shortChannelID]. Resolves the funding
    # txid/value/script hash, hunts for the spending tx, and
    # upserts one Blockchain_Transactions row. Never raises —
    # always returns (transaction_info, success, error_msg)
    # so pool.map yields a uniform result set and run() can
    # retry just the failures.
    #
    # SpendingBlockIndex sentinel: unspent outputs are stored
    # as 999999999 (passed as a STRING — MySQL coerces it
    # into the BIGINT column).
    #
    # BUG (documented, not fixed): a spend still in the
    # mempool comes back from Electrum with height 0, which
    # is falsy — the row is then written with
    # SpendingBlockIndex = 999999999 ("unspent") but a
    # non-empty SpendingTxID: an inconsistent pair until the
    # spend confirms and a later 7-day recheck repairs it. A
    # height of -1 (unconfirmed parents) would crash the
    # INSERT into the UNSIGNED column and surface as a
    # retryable failure instead.
    #
    # Used by:
    #   - run (below) — pool.map over the pending outpoints
    ############################################################

    def retrieveAndWriteLightningBlockchainTxData(self, data):
        blockIndex, txIndex, outputIndex, shortChannelID = data
        transaction_info = (blockIndex, txIndex, outputIndex, shortChannelID)

        try:
            logger.info(f"Processing transaction {blockIndex}:{txIndex}:{outputIndex}")

            # the DB connection stays open across every Electrum
            # round-trip below — with 10 workers that is 10 idle
            # connections during slow network stretches
            with get_db_connection() as db_conn:
                with db_conn.cursor() as db_cursor:
                    # STEP 1: funding side — resolve the txid and
                    # decode the funding output
                    # ===========================================
                    tx_id, output_details = self.__get_transaction_details(blockIndex, txIndex, outputIndex)
                    if not output_details:
                        error_msg = f"Could not retrieve transaction details for {blockIndex}:{txIndex}:{outputIndex}"
                        logger.error(error_msg)
                        return (transaction_info, False, error_msg)

                    # the dumps/loads round-trip is a no-op in
                    # practice: __parse_raw_transaction emits plain
                    # floats, so DecimalEncoder never fires
                    # (leftover from a verbose-RPC data source)
                    output_details = json.loads(json.dumps(output_details, indent=4, cls=DecimalEncoder))
                    tx_output_value_btc = Decimal(str(output_details['value']))
                    tx_output_value_satoshis = int(tx_output_value_btc * Decimal('100000000'))


                    # STEP 2: spending side — script-hash history,
                    # then scan candidates for the input consuming
                    # this outpoint
                    # ============================================
                    funding_script_hash = self.__get_script_hash_from_output(output_details)
                    funding_script_hash_history = self.__send_electrum_request(self.electrum_host, self.electrum_port, "blockchain.scripthash.get_history", [funding_script_hash])

                    if funding_script_hash_history is None:
                        error_msg = f"Could not retrieve script hash history for {blockIndex}:{txIndex}:{outputIndex}"
                        logger.error(error_msg)
                        return (transaction_info, False, error_msg)

                    spending_block_height, spending_tx_id = self.__get_spending_time_for_output(tx_id, outputIndex, funding_script_hash_history)

                    # height 0 (mempool spend) is falsy and slips
                    # past this check — see the BUG note in the banner
                    if spending_block_height and spending_tx_id:
                        logger.info(f"Transaction {blockIndex}:{txIndex}:{outputIndex} ({shortChannelID}) -> SPENT in block {spending_block_height}, tx {spending_tx_id}")


                    # STEP 3: upsert — reruns refresh UpdatedDate,
                    # which drives the 7-day recheck window in run()
                    # ==============================================
                    db_cursor.execute('''
                        INSERT INTO Blockchain_Transactions (
                            ShortChannelID, FundingBlockIndex, FundingTxIndex, FundingOutputIndex,
                            FundingTxID, FundingScriptHash, Value, SpendingBlockIndex, SpendingTxID, UpdatedDate
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE())
                        ON DUPLICATE KEY UPDATE
                            FundingBlockIndex = VALUES(FundingBlockIndex),
                            FundingTxIndex = VALUES(FundingTxIndex),
                            FundingOutputIndex = VALUES(FundingOutputIndex),
                            FundingTxID = VALUES(FundingTxID),
                            FundingScriptHash = VALUES(FundingScriptHash),
                            Value = VALUES(Value),
                            SpendingBlockIndex = VALUES(SpendingBlockIndex),
                            SpendingTxID = VALUES(SpendingTxID),
                            UpdatedDate = CURDATE()
                    ''', [
                        shortChannelID,
                        blockIndex,
                        txIndex,
                        outputIndex,
                        tx_id,
                        funding_script_hash,
                        tx_output_value_satoshis,
                        spending_block_height or '999999999',  # unspent sentinel (string — MySQL coerces)
                        spending_tx_id or ''
                    ])
                    db_conn.commit()

            logger.info(f"Transaction {blockIndex}:{txIndex}:{outputIndex} processed successfully")
            return (transaction_info, True, None)

        except Exception as e:
            error_msg = f"Error processing transaction {blockIndex}:{txIndex}:{outputIndex}: {str(e)}"
            logger.error(error_msg)
            return (transaction_info, False, error_msg)






    ############################################################
    # run
    ############################################################
    #
    # Batch driver. blockRange is a MULTIPLIER of the
    # 1000-block step, not a height: run(500) starts scanning
    # at block 500,000. Walks Lightning_Channels upward in
    # 1000-block windows and processes every channel that is
    # not already known-spent and has not been checked in the
    # last 7 days — open channels are re-verified weekly to
    # catch closures. Each window goes through a 10-thread
    # pool with up to 10 retry rounds, 15 s apart. Raises
    # TransactionSyncError when outpoints remain failed after
    # all retries.
    #
    # BUG (documented, not fixed): if the retry budget is
    # exhausted purely by POOL-level exceptions (the except
    # branch of the retry loop), the leftover outpoints never
    # reach all_failed_transactions — the run then finishes
    # WITHOUT raising despite permanent failures. Also, an
    # empty Lightning_Channels table makes MAX(BlockIndex)
    # return NULL, so the "+ stepSize" arithmetic dies with a
    # TypeError.
    #
    # Used by:
    #   - synchronizeBlockchain() in blnstats/__init__.py —
    #     called as run(500)
    ############################################################

    def run(self, blockRange):
        stepSize = 1000
        max_retries = 10  # per-window retry budget, shared with pool-level errors
        retry_delay = 15  # seconds between retry rounds

        all_failed_transactions = {}  # (blockIndex, txIndex, outputIndex, shortChannelID) -> error_message
        total_transactions_attempted = 0


        # STEP 1: upper scan bound — one step past the highest
        # funding block the gossip importers have seen (crashes
        # here when Lightning_Channels is empty; see banner)
        # =====================================================
        highestChannelBlock = 0
        with get_db_connection() as db_conn:
            with db_conn.cursor() as db_cursor:
                db_cursor.execute(' SELECT MAX(BlockIndex) FROM Lightning_Channels ')
                highestChannelBlock = db_cursor.fetchone()[0] + stepSize


        # STEP 2: walk the chain upward in 1000-block windows,
        # starting at blockRange * 1000
        # ====================================================
        for fromBlock in range(blockRange * stepSize, highestChannelBlock, stepSize):
            toBlock = fromBlock + stepSize

            # this outer connection idles through the whole window,
            # including every retry sleep — only the SELECT below
            # uses it; the pool workers open their own
            with get_db_connection() as db_conn:
                with db_conn.cursor() as db_cursor:
                    # STEP 2.1: outpoints still needing a look — skip
                    # known-spent channels and anything checked within
                    # the last 7 days
                    db_cursor.execute('''
                        SELECT
                            BlockIndex,
                            TxIndex, 
                            OutputIndex,
                            ShortChannelID
                        FROM 
                            Lightning_Channels
                        WHERE 
                            BlockIndex >= %s AND BlockIndex < %s
                            AND ShortChannelID NOT IN (
                                SELECT ShortChannelID 
                                FROM Blockchain_Transactions 
                                WHERE SpendingBlockIndex <> 999999999 
                                   OR UpdatedDate >= CURDATE() - INTERVAL 7 DAY
                            )
                        ORDER BY 
                            BlockIndex, TxIndex
                    ''', [fromBlock, toBlock])

                    sqlFetchData = db_cursor.fetchall()

                    toCheck = []
                    for sqlLine in sqlFetchData:
                        blockIndex, txIndex, outputIndex, shortChannelID = sqlLine
                        toCheck.append([blockIndex, txIndex, outputIndex, shortChannelID])

                    if not toCheck:
                        logger.info(f"No transactions to process in range {fromBlock} to {toBlock}")
                        continue

                    logger.info(f"Processing {len(toCheck)} transactions from {fromBlock} to {toBlock}")
                    total_transactions_attempted += len(toCheck)

                    # STEP 2.2: 10-thread pool per window; each retry round reruns only the failures
                    transactions_to_process = toCheck
                    retry_count = 0

                    while transactions_to_process and retry_count < max_retries:
                        try:
                            with ThreadPool(10) as pool:
                                results = pool.map(self.retrieveAndWriteLightningBlockchainTxData, transactions_to_process)

                            # STEP 2.3: split the uniform (info, ok, err) results
                            successful_transactions = []
                            failed_transactions = []

                            for transaction_info, success, error_msg in results:
                                if success:
                                    successful_transactions.append(transaction_info)
                                else:
                                    failed_transactions.append((transaction_info, error_msg))
                            
                            logger.info(f"Batch {fromBlock}-{toBlock}: {len(successful_transactions)} successful, {len(failed_transactions)} failed")
                            
                            if failed_transactions:
                                logger.warning(f"Failed transactions in retry {retry_count + 1}: {[t[0] for t, _ in failed_transactions]}")
                                if retry_count < max_retries - 1:
                                    transactions_to_process = [[t[0], t[1], t[2], t[3]] for (t, _) in failed_transactions]
                                    logger.info(f"Waiting {retry_delay} seconds before retrying {len(transactions_to_process)} failed transactions...")
                                    time.sleep(retry_delay)
                                else:
                                    # last round — record as permanently failed.
                                    # NOTE: transactions_to_process is NOT trimmed
                                    # here, so the count logged after the loop is
                                    # the number that ENTERED this round, not the
                                    # number that actually failed in it
                                    for transaction_info, error_msg in failed_transactions:
                                        logger.error(f"Transaction {transaction_info} permanently failed after {max_retries} attempts: {error_msg}")
                                        all_failed_transactions[transaction_info] = error_msg
                            else:
                                transactions_to_process = []  # All transactions successful
                                
                        except Exception as e:
                            # BUG (documented, not fixed): if the retry
                            # budget runs out through THIS branch, the
                            # leftover outpoints never reach
                            # all_failed_transactions and the sync ends
                            # without raising — see the banner
                            logger.error(f"Pool error processing transactions {fromBlock} to {toBlock} (attempt {retry_count + 1}): {e}")
                            if retry_count < max_retries - 1:
                                logger.info(f"Waiting {retry_delay} seconds before retrying due to pool error...")
                                time.sleep(retry_delay)

                        retry_count += 1

                    if not transactions_to_process:
                        logger.info(f"Batch {fromBlock}-{toBlock} completed successfully")
                    else:
                        logger.error(f"Batch {fromBlock}-{toBlock} completed with {len(transactions_to_process)} permanently failed transactions")


        # STEP 3: one permanent failure anywhere fails the whole
        # sync — the workflow shows red instead of silently
        # missing channels
        # ======================================================
        if all_failed_transactions:
            logger.error(f"Sync completed with {len(all_failed_transactions)} permanently failed transactions out of {total_transactions_attempted} attempted")
            raise TransactionSyncError(all_failed_transactions, total_transactions_attempted)

        logger.info(f"Sync completed successfully. All {total_transactions_attempted} transactions processed.")
