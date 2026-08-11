############################################################
#  [*] LND DBReader JSON import
#
#  Imports a gossip dump produced by the external
#  "LND DBReader" tool — a JSON export of an LND node's
#  gossip store with channel_announcements,
#  node_announcements and node_addresses arrays under a
#  top-level 'data' key — into the _LND_DBReader_* staging
#  tables, then promotes the channel announcements into the
#  shared Lightning_Channels table.
#
#  Neighbours: the dump arrives as a .json.gz URL (the
#  faculty LND node, or this site's own /rawdata mirror of
#  the '--latest' copy saved by __download_data) or as a
#  local file. Staged rows flow on to compare_sources.py
#  (source cross-check) and to EntityClusters (node-alias
#  import in blnstats/__init__.py importLNDDBReader);
#  Lightning_Channels is also fed by ln_research.py.
############################################################


import json
from datetime import datetime
import gzip
import requests
from ..database.utils import get_db_connection
import hashlib
import os
import shutil








############################################################
# LNDDBReader
############################################################
#
# Instantiating the class runs the whole import — every step
# happens in __init__. Unlike the frozen LN Research
# snapshot, this source is a LIVING export re-imported over
# time, so node rows are upserted with widening
# FirstSeen/LastSeen windows instead of being replaced.
# NOTE: _LND_DBReader_NodeAddresses is written here but no
# backend code reads it at the moment.
#
# Used by:
#   - blnstats/__init__.py importLNDDBReader() — reached from
#     main.py --import-lnd-dbreader-data (CLI) and from the
#     workflows.py task import_lnd_dbreader_data
#     (lnd_dbreader_import_flow, lnd_dbreader_full_update_flow
#     and full_initialization_flow)
############################################################

class LNDDBReader:






    ############################################################
    # __init__
    ############################################################
    #
    # The constructor IS the pipeline: download when the
    # source is a URL, parse the JSON, create the staging
    # tables, write the rows, promote the channels. There is
    # nothing to call afterwards.
    #
    # Used by:
    #   - blnstats/__init__.py importLNDDBReader() — the only
    #     caller; see the class banner for the full chain
    ############################################################

    def __init__(self, file_path):
        # STEP 1: remember the source; a URL is downloaded to
        # /DATA/INPUT first so file_path is local from here on
        # ====================================================
        self.file_path = file_path

        if(file_path.startswith('http')):
            print(f"[*] Downloading LND DBReader data from '{file_path}'")
            self.file_path = self.__download_data(file_path)


        # STEP 2: parse the dump — self.data is the 'data' dict
        # =====================================================
        print(f"[*] Reading LND DBReader data from '{self.file_path}'")
        self.data = self.__read_file()


        # STEP 3: make sure the _LND_DBReader_* staging tables exist
        # ==========================================================
        print("[*] Creating tables if not exists")
        self.create_tables_if_not_exists()


        # STEP 4: write the three data arrays into the staging tables
        # ===========================================================
        print("[*] Writing data to database")
        self.import_data()


        # STEP 5: promote channel announcements into the shared
        # Lightning_Channels table
        # =====================================================
        print("[*] Inserting data into main system table (DB Table: Lightning_Channels)")
        self.insert_or_ignore_into_main()

        print("[*] Done importing LND DBReader data")






    ############################################################
    # __download_data
    ############################################################
    #
    # Saves the dump under /DATA/INPUT as
    # lnd-dbreader-<ID>--<timestamp>.json.gz, where <ID> is
    # the first 8 hex chars of the URL's SHA-256 — one
    # timestamped series per source URL. Every run downloads
    # afresh (no cache-skip like ln_research.py): that is what
    # builds the series. A copy also lands on
    # lnd-dbreader-<ID>--latest.json.gz; that '--latest' file
    # is what full_initialization_flow (workflows.py) pulls
    # back in through this site's public /rawdata/INPUT/ URL.
    # _tmp-then-rename keeps a crashed download from leaving a
    # half-written file under the final name. Only .gz URLs
    # are accepted — anything else raises ValueError.
    #
    # Used by:
    #   - __init__ (above) — when the source is an http(s) URL
    ############################################################

    def __download_data(self, url):
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        addressHashID = hashlib.sha256(url.encode()).hexdigest()[:8].upper()
        timeNow = datetime.now().strftime('%Y%m%d-%H%M%S')
        file_path = f"/DATA/INPUT/lnd-dbreader-{addressHashID}--{timeNow}"
        file_path_latest = f"/DATA/INPUT/lnd-dbreader-{addressHashID}--latest.json.gz"
        if(self.file_path.endswith('.gz')):
            with open(f"{file_path}.json.gz_tmp", 'wb') as file:
                file.write(response.content)
            os.rename(f"{file_path}.json.gz_tmp", f"{file_path}.json.gz")
            shutil.copy(f"{file_path}.json.gz", file_path_latest)
            return f"{file_path}.json.gz"
        else:
            raise ValueError(f"Unsupported file type: {self.file_path}")






    ############################################################
    # __read_file
    ############################################################
    #
    # Loads the dump and returns only its 'data' payload;
    # .gz vs plain JSON is decided by the file extension.
    #
    # Used by:
    #   - __init__ (above)
    ############################################################

    def __read_file(self):
        if(self.file_path.endswith('.gz')):
            with gzip.open(self.file_path, 'rt') as file:
                return json.load(file)['data']
        else:
            with open(self.file_path, 'r') as file:
                return json.load(file)['data']






    ############################################################
    # create_tables_if_not_exists
    ############################################################
    #
    # Creates the three _LND_DBReader_* staging tables — the
    # same shapes as their _LNResearch_* twins, so
    # compare_sources.py can query both sides symmetrically.
    # Public (unlike ln_research.py's name-mangled version),
    # but nothing outside this class calls it at the moment.
    #
    # Used by:
    #   - __init__ (above)
    ############################################################

    def create_tables_if_not_exists(self):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS `_LND_DBReader_ChannelAnnouncements` (
                        `ShortChannelID` BIGINT NOT NULL,
                        `BlockIndex` INT NOT NULL,
                        `TxIndex` INT NOT NULL,
                        `OutputIndex` INT NOT NULL,
                        `NodeID1` CHAR(66) NOT NULL,
                        `NodeID2` CHAR(66) NOT NULL,
                        CONSTRAINT `PRIMARY` PRIMARY KEY (`ShortChannelID`),
                        CONSTRAINT `idx_ShortChannelID` UNIQUE (`ShortChannelID`)
                    );
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS `_LND_DBReader_NodeAnnouncements` ( 
                        `ID` INT AUTO_INCREMENT NOT NULL,
                        `NodeID` CHAR(66) NOT NULL,
                        `Alias` VARCHAR(32) NOT NULL,
                        `FirstSeen` INT NOT NULL,
                        `LastSeen` INT NOT NULL,
                        CONSTRAINT `PRIMARY` PRIMARY KEY (`ID`),
                        CONSTRAINT `unique_nodeid_alias` UNIQUE (`NodeID`, `Alias`)
                    );
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS `_LND_DBReader_NodeAddresses` ( 
                        `ID` INT AUTO_INCREMENT NOT NULL,
                        `NodeID` CHAR(66) NOT NULL,
                        `Address` VARCHAR(255) NOT NULL,
                        `Port` INT NOT NULL,
                        `FirstSeen` INT NOT NULL,
                        `LastSeen` INT NOT NULL,
                        CONSTRAINT `PRIMARY` PRIMARY KEY (`ID`),
                        CONSTRAINT `unique_nodeid_address_port` UNIQUE (`NodeID`, `Address`, `Port`)
                    );
                ''')
                conn.commit()






    ############################################################
    # import_data
    ############################################################
    #
    # Writes the three 'data' arrays row by row over one
    # connection, one commit per pass: channel announcements
    # via INSERT IGNORE (immutable facts), node announcements
    # and node addresses upserted with FirstSeen = LEAST /
    # LastSeen = GREATEST so repeated imports only WIDEN each
    # sighting window. Public, but nothing outside this class
    # calls it at the moment.
    #
    # Used by:
    #   - __init__ (above)
    ############################################################

    def import_data(self):
        # STEP 1: one connection and cursor for all three
        # passes — commits happen per pass, not per row
        # ===============================================
        with get_db_connection() as conn:
            with conn.cursor() as cursor:


                # STEP 2: channel announcements — INSERT IGNORE
                # =============================================
                print("[*] Inserting channel announcements into _LND_DBReader_ChannelAnnouncements table (INSERT OR IGNORE)")
                for item in self.data['channel_announcements']:

                    # ShortChannelID packs block height / tx
                    # index / output index as 24 + 24 + 16 bits
                    short_channel_id = item['ShortChannelID']
                    block_height = (short_channel_id >> 40) & 0xFFFFFF
                    tx_index = (short_channel_id >> 16) & 0xFFFFFF
                    output_index = short_channel_id & 0xFFFF

                    node_id_1 = item['NodeID1']
                    node_id_2 = item['NodeID2']

                    cursor.execute('''
                        INSERT IGNORE INTO _LND_DBReader_ChannelAnnouncements 
                            (ShortChannelID, BlockIndex, TxIndex, OutputIndex, NodeID1, NodeID2) VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (short_channel_id, block_height, tx_index, output_index, node_id_1, node_id_2))
                conn.commit()


                # STEP 3: node announcements — widening upsert
                # ============================================
                print("[*] Inserting node announcements into _LND_DBReader_NodeAnnouncements table (INSERT OR UPDATE)")
                for item in self.data['node_announcements']:
                    node_id = item['NodeID']
                    alias = item['Alias']
                    first_seen = item['FirstSeen']
                    last_seen = item['LastSeen']

                    cursor.execute('''
                        INSERT INTO _LND_DBReader_NodeAnnouncements
                            (NodeID, Alias, FirstSeen, LastSeen) VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            FirstSeen = LEAST(FirstSeen, VALUES(FirstSeen)),
                            LastSeen = GREATEST(LastSeen, VALUES(LastSeen))
                    ''', (node_id, alias, first_seen, last_seen))
                conn.commit()


                # STEP 4: node addresses — widening upsert
                # ========================================
                print("[*] Inserting node addresses into _LND_DBReader_NodeAddresses table (INSERT OR UPDATE)")
                for item in self.data['node_addresses']:
                    node_id = item['NodeID']
                    address = item['Address']
                    port = item['Port']
                    first_seen = item['FirstSeen']
                    last_seen = item['LastSeen']

                    cursor.execute('''
                        INSERT INTO _LND_DBReader_NodeAddresses
                            (NodeID, Address, Port, FirstSeen, LastSeen) VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            FirstSeen = LEAST(FirstSeen, VALUES(FirstSeen)),
                            LastSeen = GREATEST(LastSeen, VALUES(LastSeen))
                    ''', (node_id, address, port, first_seen, last_seen))
                conn.commit()






    ############################################################
    # insert_or_ignore_into_main
    ############################################################
    #
    # Promotes the staged channel announcements into the
    # shared Lightning_Channels table. INSERT IGNORE — rows
    # already promoted (e.g. by the LN Research import) stay
    # untouched. Announcements claiming a funding block
    # before SegWit activation (481,824) are dropped: no
    # real LN channel can predate SegWit, and the 2026-08
    # production audit found 3,984 bogus block-500 SCIDs in
    # this dump. Public, but nothing outside this class
    # calls it at the moment.
    #
    # Used by:
    #   - __init__ (above) — final pipeline step
    ############################################################

    def insert_or_ignore_into_main(self):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT IGNORE INTO Lightning_Channels
                        (ShortChannelID, BlockIndex, TxIndex, OutputIndex, NodeID1, NodeID2)
                    SELECT
                        ca.ShortChannelID,
                        ca.BlockIndex,
                        ca.TxIndex,
                        ca.OutputIndex,
                        ca.NodeID1,
                        ca.NodeID2
                    FROM _LND_DBReader_ChannelAnnouncements ca
                    WHERE ca.BlockIndex >= 481824
                ''')
                conn.commit()
