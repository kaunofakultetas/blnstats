############################################################
#  [*] Blockchain blocks — height/hash/time index import
#
#  Mirrors the Bitcoin block index into Blockchain_Blocks:
#  for every height it fetches the 80-byte block header from
#  Electrum, hashes it into the block hash and lifts the
#  timestamp straight out of the raw bytes. The table is the
#  height -> date lookup the rest of the system leans on.
#
#  Neighbours: driven only by synchronizeBlockchain() in
#  blnstats/__init__.py, which runs it before AND after the
#  transaction import in blockchain_transactions.py so that
#  freshly referenced blocks exist; Blockchain_Blocks flows
#  on to database/raw_data_selector.py (first block of each
#  day), calculations/general_stats.py and
#  data_import/compare_sources.py.
#
#  Wire-format ground rules used throughout:
#    - Electrum speaks newline-delimited JSON-RPC over a
#      plain TCP socket (no TLS)
#    - a block header is EXACTLY 80 bytes; its hash is
#      double-sha256 of those bytes, byte-reversed into
#      display order
#    - the timestamp is a 4-byte little-endian UNIX time at
#      header offset 68
############################################################


import logging
import socket
import json
import hashlib
import time
from multiprocessing.dummy import Pool as ThreadPool
from ..database.utils import get_db_connection
from datetime import datetime
from zoneinfo import ZoneInfo

# The Time/Date columns are rendered in THIS zone, pinned so
# the dataset never shifts with the host's TZ setting. The
# whole 2018+ history and every published monthly snapshot
# use Vilnius day boundaries — see README "Methodology
# notes" before ever changing this (a UTC switch re-selects
# nearly every monthly first block).
DISPLAY_TZ = ZoneInfo('Europe/Vilnius')
from dataclasses import dataclass
from typing import List, Dict

# NOTE: `dataclass` and `List` are imported above but never
# used anywhere in this module — dead imports.

# basicConfig at import time: whichever blnstats module is
# imported first wins the root-logger configuration.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)








############################################################
# BlockSyncError
############################################################
#
# Terminal failure signal of a block sync: raised once at
# the end of BlockchainBlocks.sync_blocks() when heights are
# still failing after every retry round. Carries the
# height -> error map so the log shows exactly which blocks
# never landed. Also raised as BlockSyncError({}, 0) when
# the chain tip cannot be fetched at all.
#
# Used by:
#   - BlockchainBlocks.sync_blocks (below) — the only raise
#     site; nothing catches it upstream, so it aborts the
#     --sync-blockchain CLI run / synchronize_blockchain
#     workflow task
############################################################

class BlockSyncError(Exception):






    ############################################################
    # __init__
    ############################################################
    #
    # Builds the message eagerly so a bare str(exc) in the
    # workflow log already names every failed height. NOTE:
    # for the empty tip-fetch case the message misleadingly
    # reads "Failed to sync 0 out of 0 blocks".
    #
    # Used by:
    #   - BlockchainBlocks.sync_blocks (below)
    ############################################################

    def __init__(self, failed_blocks: Dict[int, str], total_blocks_attempted: int):
        self.failed_blocks = failed_blocks
        self.total_blocks_attempted = total_blocks_attempted
        self.failed_count = len(failed_blocks)
        
        message = (f"Failed to sync {self.failed_count} out of {total_blocks_attempted} blocks. "
                  f"Failed block heights: {list(failed_blocks.keys())}")
        super().__init__(message)








############################################################
# send_electrum_request
############################################################
#
# One Electrum JSON-RPC call over a fresh plain TCP socket
# (newline-delimited JSON, no TLS). Reads until the first
# chunk containing a LF — safe because Electrum answers a
# single request with a single LF-terminated line. Returns
# the 'result' payload, or None on any network/protocol
# error (errors are logged, never raised). NOTE: this is a
# near-duplicate of the private __send_electrum_request in
# blockchain_transactions.py — fix bugs in both places. The
# socket is only closed on the happy path; an exception
# mid-request leaks the descriptor until the GC collects it.
#
# Used by:
#   - retrieve_and_write_blockchain_block (below)
#   - BlockchainBlocks.sync_blocks (below)
############################################################

def send_electrum_request(server_ip: str, server_port: int, method: str, params: list):
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
# get_block_hash_from_header
############################################################
#
# 80-byte header hex -> block hash: sha256(sha256(header)),
# byte-reversed into the display order used by explorers and
# stored in the BlockHash column.
#
# Used by:
#   - retrieve_and_write_blockchain_block (below)
############################################################

def get_block_hash_from_header(header_hex: str) -> str:
    header_bytes = bytes.fromhex(header_hex)
    hash1 = hashlib.sha256(header_bytes).digest()
    hash2 = hashlib.sha256(hash1).digest()
    return hash2[::-1].hex()








############################################################
# retrieve_and_write_blockchain_block
############################################################
#
# Worker for ONE block height, run through the thread pool
# in sync_blocks. Sits at module level (with args packed as
# a (height, credentials) tuple) so pool.map can call it.
# Fetches the raw header, derives hash and timestamp locally
# — no further Electrum round-trips — and upserts one
# Blockchain_Blocks row. Never raises: always returns
# (height, success, error_message) so the pool result set is
# uniform and sync_blocks can retry just the failures.
#
# Time/Date are rendered in the pinned Europe/Vilnius zone
# (DISPLAY_TZ above) — host-TZ-independent and consistent
# with the entire existing dataset. The Timestamp column
# stays the raw UTC UNIX time, so a UTC view is always one
# FROM_UNIXTIME away.
#
# Used by:
#   - BlockchainBlocks.sync_blocks (below) — pool.map over
#     the missing heights
############################################################

def retrieve_and_write_blockchain_block(args):
    height, electrum_credentials = args
    electrum_host = electrum_credentials['host']
    electrum_port = electrum_credentials['port']

    try:
        # STEP 1: fetch the raw 80-byte header for this height
        # ====================================================
        raw_header = send_electrum_request(electrum_host, electrum_port, 'blockchain.block.header', [height])
        if not raw_header:
            logger.error(f"Could not retrieve header for block {height}")
            return (height, False, "Could not retrieve header")


        # STEP 2: derive everything locally — the block hash by
        # double-sha256, the timestamp from the 4-byte
        # little-endian field at header offset 68
        # =====================================================
        block_hash = get_block_hash_from_header(raw_header)

        header_bytes = bytes.fromhex(raw_header)
        timestamp = int.from_bytes(header_bytes[68:72], 'little')

        # pinned Europe/Vilnius rendering — see DISPLAY_TZ and
        # the banner note
        dt_object = datetime.fromtimestamp(timestamp, tz=DISPLAY_TZ)
        human_readable_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')
        human_readable_date = human_readable_time.split()[0]


        # STEP 3: upsert, so re-syncs and reorg refreshes stay
        # idempotent
        # ====================================================
        with get_db_connection() as db_conn:
            with db_conn.cursor() as db_cursor:
                db_cursor.execute('''
                    INSERT INTO `Blockchain_Blocks` 
                        (`BlockHeight`, `BlockHash`, `Timestamp`, `Time`, `Date`) VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        BlockHash = VALUES(BlockHash),
                        Timestamp = VALUES(Timestamp),
                        Time = VALUES(Time),
                        Date = VALUES(Date)
                ''', (
                    height,
                    block_hash,
                    timestamp,
                    human_readable_time,
                    human_readable_date
                ))
                db_conn.commit()
        
        logger.info(f"Block {height} inserted into database.")
        return (height, True, None)
        
    except Exception as e:
        error_msg = f"Error processing block {height}: {str(e)}"
        logger.error(error_msg)
        return (height, False, error_msg)








############################################################
# BlockchainBlocks
############################################################
#
# Importer that keeps the local Bitcoin block index
# complete: finds every height missing from
# Blockchain_Blocks up to the current chain tip and fills
# the gaps through a small thread pool. Patient by design —
# up to 120 retry rounds, 60 s apart, per 10000-block batch
# — so an unattended sync survives long Electrum outages.
#
# Used by:
#   - synchronizeBlockchain() in blnstats/__init__.py — the
#     only constructor call; invoked twice per sync (before
#     and after the transaction import) and reached from
#     main.py --sync-blockchain and the
#     synchronize_blockchain task in workflows.py
############################################################

class BlockchainBlocks:






    ############################################################
    # __init__
    ############################################################
    #
    # Stores the Electrum endpoint and makes sure the target
    # table exists. No Electrum connection is opened here —
    # every request later dials a fresh socket.
    #
    # Used by:
    #   - synchronizeBlockchain() in blnstats/__init__.py
    ############################################################

    def __init__(self, electrum_host: str, electrum_port: int):
        self.electrum_host = electrum_host
        self.electrum_port = electrum_port

        self.__create_tables_if_not_exist()






    ############################################################
    # __create_tables_if_not_exist
    ############################################################
    #
    # DDL for Blockchain_Blocks: one row per height with the
    # block hash, the raw UNIX timestamp and its
    # (server-local) DATETIME / DATE renderings. NOTE:
    # database/utils.py create_tables_if_not_exists() carries
    # a second, equivalent copy of this DDL — keep the two in
    # step.
    #
    # Used by:
    #   - __init__ (above)
    ############################################################

    def __create_tables_if_not_exist(self):
        with get_db_connection() as db_conn:
            with db_conn.cursor() as db_cursor:
                db_cursor.execute('''
                    CREATE TABLE IF NOT EXISTS `Blockchain_Blocks` (
                        `BlockHeight` INT UNSIGNED NOT NULL UNIQUE,
                        `BlockHash` CHAR(64) NOT NULL,
                        `Timestamp` INT UNSIGNED NOT NULL,
                        `Time` DATETIME NOT NULL,
                        `Date` DATE NOT NULL,
                        PRIMARY KEY (`BlockHeight`),
                        INDEX `idx_BlockHash` (`BlockHash`),
                        INDEX `idx_Timestamp` (`Timestamp`),
                        INDEX `idx_Date` (`Date`)
                    );
                ''')






    ############################################################
    # sync_blocks
    ############################################################
    #
    # Batch driver: walks 0..chain-tip in 10000-block
    # batches, asks the DB which heights already exist, and
    # pushes only the missing ones through a 4-thread pool
    # (ThreadPool from multiprocessing.dummy — threads, not
    # processes, despite the variable name). Raises
    # BlockSyncError when heights remain failed after all
    # retry rounds, or immediately (as BlockSyncError({}, 0))
    # when the chain tip cannot be fetched.
    #
    # As in BlockchainTransactions.run, exhausting a batch's
    # retry budget records every leftover height — including
    # ones whose rounds only ever died at pool level — so the
    # final check always raises.
    #
    # Used by:
    #   - synchronizeBlockchain() in blnstats/__init__.py —
    #     twice per sync (before and after the transaction
    #     import)
    ############################################################

    def sync_blocks(self):
        # STEP 1: current chain tip via headers.subscribe (the
        # reply also carries the tip header; only the height is
        # used)
        # =====================================================
        latest_header = send_electrum_request(self.electrum_host, self.electrum_port, 'blockchain.headers.subscribe', [])
        if not latest_header:
            logger.error("Could not get latest block from Electrum server.")
            raise BlockSyncError({}, 0)
        latest_blockchain_height = latest_header['height']

        # packed per task because the worker is a module-level
        # function, not a method
        electrum_credentials = {
            'host': self.electrum_host,
            'port': self.electrum_port
        }

        processes = 4  # ThreadPool size — threads, not processes
        batch_size = 10000
        max_retries = 120  # very patient: up to 120 x 60 s = 2 h per batch
        retry_delay = 60  # seconds between retry rounds

        all_failed_blocks = {}  # height -> error_message
        total_blocks_attempted = 0


        # STEP 2: walk the whole chain in 10000-block batches
        # ===================================================
        for batch_start in range(0, latest_blockchain_height + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, latest_blockchain_height)
            all_heights = list(range(batch_start, batch_end + 1))

            # STEP 2.1: heights already present in this batch
            with get_db_connection() as db_conn:
                with db_conn.cursor() as db_cursor:
                    db_cursor.execute('''
                        SELECT `BlockHeight` FROM `Blockchain_Blocks`
                        WHERE `BlockHeight` BETWEEN %s AND %s
                    ''', (batch_start, batch_end))
                    existing_blocks = db_cursor.fetchall()
                    existing_heights = set(row[0] for row in existing_blocks)

            # STEP 2.2: the gap list — normally empty except near the tip
            missing_heights = [height for height in all_heights if height not in existing_heights]

            if not missing_heights:
                logger.info(f"All blocks from {batch_start} to {batch_end} already exist in the database. Skipping batch.")
                continue

            logger.info(f"Syncing missing blocks {missing_heights[0]} to {missing_heights[-1]} in batch {batch_start} to {batch_end}")
            total_blocks_attempted += len(missing_heights)

            # STEP 2.3: 4-thread pool; each retry round reruns only the failures
            blocks_to_process = missing_heights
            retry_count = 0

            while blocks_to_process and retry_count < max_retries:
                tasks = [(height, electrum_credentials) for height in blocks_to_process]

                try:
                    with ThreadPool(processes) as pool:
                        results = pool.map(retrieve_and_write_blockchain_block, tasks)

                    # STEP 2.4: split the uniform (height, ok, err) results
                    successful_blocks = []
                    failed_blocks = []

                    for height, success, error_msg in results:
                        if success:
                            successful_blocks.append(height)
                        else:
                            failed_blocks.append((height, error_msg))
                    
                    logger.info(f"Batch {batch_start}-{batch_end}: {len(successful_blocks)} successful, {len(failed_blocks)} failed")
                    
                    if failed_blocks:
                        logger.warning(f"Failed blocks in retry {retry_count + 1}: {[h for h, _ in failed_blocks]}")
                        # trim to the actual failures so the batch log and
                        # the exhaustion accounting below see the real
                        # leftover set, not the round's input
                        blocks_to_process = [h for h, _ in failed_blocks]
                        if retry_count < max_retries - 1:
                            logger.info(f"Waiting {retry_delay} seconds before retrying {len(blocks_to_process)} failed blocks...")
                            time.sleep(retry_delay)
                        else:
                            # last round — record as permanently failed
                            for height, error_msg in failed_blocks:
                                logger.error(f"Block {height} permanently failed after {max_retries} attempts: {error_msg}")
                                all_failed_blocks[height] = error_msg
                    else:
                        blocks_to_process = []  # All blocks successful
                        
                except Exception as e:
                    logger.error(f"Pool error syncing blocks {batch_start} to {batch_end} (attempt {retry_count + 1}): {e}")
                    if retry_count < max_retries - 1:
                        logger.info(f"Waiting {retry_delay} seconds before retrying due to pool error...")
                        time.sleep(retry_delay)

                retry_count += 1

            if not blocks_to_process:
                logger.info(f"Batch {batch_start}-{batch_end} completed successfully")
            else:
                # retry budget exhausted — heights whose final rounds
                # died at pool level were never recorded by the
                # last-round branch above; catch them here so STEP 3
                # still raises (setdefault keeps the more specific
                # per-height message when one exists)
                for leftover in blocks_to_process:
                    all_failed_blocks.setdefault(leftover, "retry budget exhausted (pool-level errors)")
                logger.error(f"Batch {batch_start}-{batch_end} completed with {len(blocks_to_process)} permanently failed blocks")


        # STEP 3: one permanent failure anywhere fails the whole
        # sync — the workflow shows red instead of silently
        # missing blocks
        # ======================================================
        if all_failed_blocks:
            logger.error(f"Sync completed with {len(all_failed_blocks)} permanently failed blocks out of {total_blocks_attempted} attempted")
            raise BlockSyncError(all_failed_blocks, total_blocks_attempted)

        logger.info(f"Sync completed successfully. All {total_blocks_attempted} blocks synced.")
