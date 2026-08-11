############################################################
#  [*] LN Research gossip snapshot import
#
#  Imports the public LN Research dataset — a bz2-compressed
#  capture of raw Lightning Network gossip messages — into
#  the _LNResearch_* staging tables, then promotes the
#  channel announcements into the shared Lightning_Channels
#  table.
#
#  Neighbours: the snapshot comes from the lnresearch bucket
#  on Google Cloud Storage (or a local .gsp.bz2 path).
#  Staged rows flow on to compare_sources.py (source
#  cross-check) and to EntityClusters (node-alias import in
#  blnstats/__init__.py); Lightning_Channels is also fed by
#  lnd_dbreader.py.
############################################################


import bz2
from pyln.proto.primitives import varint_decode
import base64
from ..database.utils import get_db_connection
import requests
import os


# Default snapshot — the newest capture published by the
# lnresearch project (2023-09-24). __init__ falls back to it
# when no path is given.
LATEST_LN_RESEARCH_DOWNLOAD_URL = "https://storage.googleapis.com/lnresearch/gossip-20230924.gsp.bz2"








############################################################
# LNResearchData
############################################################
#
# Parses an LN Research gossip capture (channel
# announcements, node announcements, channel updates) and
# stages it in _LNResearch_ChannelAnnouncements /
# _LNResearch_NodeAnnouncements / _LNResearch_NodeAddresses.
# Instantiating the class runs the whole import — every step
# happens in __init__. NOTE: _LNResearch_NodeAddresses is
# written here but no backend code reads it at the moment.
#
# Used by:
#   - main.py --import-ln-research-data (CLI)
#   - blnstats/__init__.py importLNResearchData() — the
#     Prefect route (workflows.py task
#     import_ln_research_data), which also folds the
#     imported aliases into the entity tables afterwards
############################################################

class LNResearchData:
    # Class-level default source; __init__ shadows it with an
    # instance attribute when a path is passed in
    file_path = LATEST_LN_RESEARCH_DOWNLOAD_URL






    ############################################################
    # __init__
    ############################################################
    #
    # The constructor IS the pipeline: resolve the source,
    # download it when it is a URL, create the staging tables,
    # replay the capture into them, promote the channels.
    # There is nothing to call afterwards.
    #
    # Used by:
    #   - main.py --import-ln-research-data (CLI) — the only
    #     working caller; see the bug note in the class banner
    ############################################################

    def __init__(self, file_path : str = None):
        # STEP 1: resolve the source — an explicit argument
        # overrides the class-level default snapshot URL
        # =================================================
        if(file_path != None):
            self.file_path = file_path


        # STEP 2: a URL source is fetched to /DATA/INPUT first,
        # so from here on file_path is always a local path
        # =====================================================
        if(self.file_path.startswith('http')):
            print(f"[*] Downloading LN Research dataset from '{self.file_path}'")
            self.file_path = self.__download_data(self.file_path)


        # STEP 3: make sure the _LNResearch_* staging tables exist
        # ========================================================
        print(f"[*] Creating tables if not exists")
        self.__create_tables_if_not_exists()


        # STEP 4: replay the capture into the staging tables
        # ==================================================
        print(f"[*] Importing LN Research dataset from '{self.file_path}' into _LNResearch_XXXX DB tables")
        self.__import_data(self.file_path)


        # STEP 5: promote channel announcements into the shared
        # Lightning_Channels table
        # =====================================================
        print("[*] Inserting data into main system table (DB Table: Lightning_Channels)")
        self.insert_or_ignore_into_main()

        print("[*] Done importing LN Research data")






    ############################################################
    # __download_data
    ############################################################
    #
    # Fetches the snapshot into /DATA/INPUT/<basename of URL>.
    # An already-downloaded copy wins — published snapshots
    # are immutable, so re-downloading only wastes bandwidth.
    #
    # Used by:
    #   - __init__ (above) — when the source is an http(s) URL
    ############################################################

    def __download_data(self, url):
        file_path = f"/DATA/INPUT/{url.split('/')[-1]}"
        if(os.path.exists(file_path)):
            print(f"[*] File already exists at '{file_path}'")
            return file_path

        # response.content buffers the whole snapshot in RAM;
        # timeout=30 guards each socket read, not the whole
        # transfer
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # _tmp-then-rename: a crashed download never leaves a
        # half-written file under the final name
        with open(file_path+'_tmp', 'wb') as file:
            file.write(response.content)
        os.rename(file_path+'_tmp', file_path)
        return file_path






    ############################################################
    # __parse_message
    ############################################################
    #
    # Decodes ONE raw gossip message and stages it. Wire
    # format is BOLT #7: bytes 0-1 carry the big-endian type —
    # 256 channel_announcement, 257 node_announcement, 258
    # channel_update (recognised but deliberately dropped; the
    # commented-out block below is the dormant parser for it).
    # Field offsets shift with the variable-length features
    # field, hence all the features_len arithmetic.
    #
    # Dead code (documented, not fixed): features, chain_hash,
    # bitcoin_key_1/2 (type 256) and signature, features,
    # rgb_color, addresses (type 257) are computed but never
    # used; addressType drives the .onion conversion but is
    # never stored (the table has no column for it); the
    # addressID counter is incremented but never read. The
    # return value is meaningless too — '' for unknown types,
    # None otherwise — and the caller ignores it.
    #
    # Used by:
    #   - __import_data (below) — once per replayed message
    ############################################################

    def __parse_message(self, db_cursor, msg: bytes):
        # Bytes 0-1: big-endian BOLT #7 message type
        msg_type = int.from_bytes(msg[:2], byteorder='big')

        # channel_announcement — four 64-byte signatures sit in
        # front, so the features length lives at offset 258
        if msg_type == 256:
            features_len = int.from_bytes(msg[258:260], byteorder='big')
            features = msg[260:260+features_len].hex()
            chain_hash = msg[260+features_len:292+features_len].hex()
            short_channel_id = int.from_bytes(msg[292+features_len:300+features_len], byteorder='big')
            # ShortChannelID packs block height / tx index /
            # output index as 24 + 24 + 16 bits
            block_height = (short_channel_id >> 40) & 0xFFFFFF
            tx_index = (short_channel_id >> 16) & 0xFFFFFF
            output_index = short_channel_id & 0xFFFF
            node_id_1 = msg[300+features_len:333+features_len].hex()
            node_id_2 = msg[333+features_len:366+features_len].hex()
            bitcoin_key_1 = msg[366+features_len:399+features_len].hex()
            bitcoin_key_2 = msg[399+features_len:432+features_len].hex()

            db_cursor.execute(f'''
                INSERT IGNORE INTO _LNResearch_ChannelAnnouncements 
                    (ShortChannelID, BlockIndex, TxIndex, OutputIndex, NodeID1, NodeID2) VALUES (%s, %s, %s, %s, %s, %s)
            ''', [
                short_channel_id,
                block_height,
                tx_index,
                output_index,
                node_id_1,
                node_id_2
            ])



        # node_announcement — the alias is a fixed 32-byte
        # field, NUL-padded on the wire (hence the rstrip);
        # the packed address block goes to __parse_addresses
        elif msg_type == 257:
            signature = msg[2:66].hex()
            features_len = int.from_bytes(msg[66:68], byteorder='big')
            features = msg[68:68+features_len].hex()
            timestamp = int.from_bytes(msg[68+features_len:72+features_len], byteorder='big')
            node_id = msg[72+features_len:105+features_len].hex()
            rgb_color = msg[105+features_len:108+features_len].hex()
            alias = msg[108+features_len:140+features_len].decode('utf-8', errors='ignore').rstrip('\x00')
            addrlen = int.from_bytes(msg[140+features_len:142+features_len], byteorder='big')
            addresses = msg[142+features_len:142+features_len+addrlen].hex()
            addresses_data = msg[142+features_len:142+features_len+addrlen]
            parsed_addresses = self.__parse_addresses(addresses_data)

            # Upsert: repeated announcements only WIDEN the
            # FirstSeen/LastSeen window, never shrink it
            db_cursor.execute(f'''
                INSERT INTO _LNResearch_NodeAnnouncements
                    (NodeID, Alias, FirstSeen, LastSeen) VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    FirstSeen = LEAST(FirstSeen, VALUES(FirstSeen)),
                    LastSeen = GREATEST(LastSeen, VALUES(LastSeen))
            ''', [
                node_id,
                alias,
                timestamp,
                timestamp
            ])

            addressID = 0
            for parsed_address in parsed_addresses:
                nodeAddress = parsed_address[0]
                nodePort = parsed_address[1]
                # Family is inferred from the textual shape —
                # Tor addresses arrive as bare hex, so their
                # LENGTH tells the generation: 20 hex chars =
                # 10-byte Tor v2, 70 hex chars = 35-byte Tor v3
                addressType = ''
                if ':' in nodeAddress:
                    addressType = 'IPv6'
                elif '.' in nodeAddress:
                    addressType = 'IPv4'
                elif len(nodeAddress) == 20:
                    nodeAddress = self.__hex_to_onion(nodeAddress)
                    addressType = 'Tor v2'
                elif len(nodeAddress) == 70:
                    nodeAddress = self.__hex_to_onion(nodeAddress)
                    addressType = 'Tor v3'

                # Same widening upsert as the announcement row
                db_cursor.execute(f'''
                    INSERT INTO _LNResearch_NodeAddresses
                        (NodeID, Address, Port, FirstSeen, LastSeen) VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        FirstSeen = LEAST(FirstSeen, VALUES(FirstSeen)),
                        LastSeen = GREATEST(LastSeen, VALUES(LastSeen))
                ''', [node_id, nodeAddress, nodePort, timestamp, timestamp])
                addressID += 1  # dead counter — never read



        # channel_update — recognised so it does not fall into
        # the unknown-type branch, but deliberately not stored.
        # The dormant parser below pairs with the commented-out
        # _LNResearch_ChannelUpdates table in
        # __create_tables_if_not_exists.
        elif msg_type == 258:
            pass
            # signature = msg[2:66].hex()
            # chain_hash = msg[66:98].hex()
            # short_channel_id = int.from_bytes(msg[98:106], byteorder='big')
            # timestamp = int.from_bytes(msg[106:110], byteorder='big')
            # message_flags = msg[110]
            # channel_flags = msg[111]
            # cltv_expiry_delta = int.from_bytes(msg[112:114], byteorder='big')
            # htlc_minimum_msat = int.from_bytes(msg[114:122], byteorder='big')
            # fee_base_msat = int.from_bytes(msg[122:126], byteorder='big')
            # fee_proportional_millionths = int.from_bytes(msg[126:130], byteorder='big')

            # db_cursor.execute(f'''
            #     INSERT IGNORE INTO _LNResearch_ChannelUpdates (
            #         signature, chain_hash, short_channel_id, timestamp, message_flags,
            #         channel_flags, cltv_expiry_delta, htlc_minimum_msat, fee_base_msat,
            #         fee_proportional_millionths
            #     ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            # ''', [
            #     signature,
            #     chain_hash,
            #     short_channel_id,
            #     timestamp,
            #     message_flags,
            #     channel_flags,
            #     cltv_expiry_delta,
            #     htlc_minimum_msat,
            #     fee_base_msat,
            #     fee_proportional_millionths
            # ])



        # Anything else is logged and skipped
        else:
            print(f"Unknown message type: {msg_type}")
            return ''






    ############################################################
    # __parse_addresses
    ############################################################
    #
    # Walks the packed address block of a node_announcement:
    # each entry is a 1-byte type, the address bytes, then a
    # 2-byte big-endian port. Types: 1 IPv4 (4 B), 2 IPv6
    # (16 B), 3 Tor v2 (10 B), 4 Tor v3 (35 B). Returns
    # (address, port) tuples; Tor addresses stay bare hex here
    # — __parse_message onions them later by hex length.
    #
    # Used by:
    #   - __parse_message (above) — node_announcement branch
    ############################################################

    def __parse_addresses(self, data):
        i = 0
        addresses = []
        while i < len(data):
            addr_type = data[i]
            i += 1
            if addr_type == 1:  # IPv4
                ip = ".".join(map(str, data[i:i+4]))
                port = int.from_bytes(data[i+4:i+6], byteorder='big')
                addresses.append((ip, port))
                i += 6
            elif addr_type == 2:  # IPv6
                ip = ":".join(["%x" % int.from_bytes(data[i+j:i+j+2], byteorder='big') for j in range(0, 16, 2)])
                port = int.from_bytes(data[i+16:i+18], byteorder='big')
                addresses.append((ip, port))
                i += 18
            elif addr_type == 3:  # Tor v2
                ip = data[i:i+10].hex()
                port = int.from_bytes(data[i+10:i+12], byteorder='big')
                addresses.append((ip, port))
                i += 12
            elif addr_type == 4:  # Tor v3
                ip = data[i:i+35].hex()
                port = int.from_bytes(data[i+35:i+37], byteorder='big')
                addresses.append((ip, port))
                i += 37
            else:
                # Unknown type ⇒ unknown length ⇒ the rest of
                # the block cannot be trusted — bail out
                break
        return addresses






    ############################################################
    # __hex_to_onion
    ############################################################
    #
    # hex → base32 (lowercase, '=' padding stripped) plus the
    # '.onion' suffix — the standard textual form of a Tor
    # hidden-service address.
    #
    # Used by:
    #   - __parse_message (above) — Tor v2/v3 node addresses
    ############################################################

    def __hex_to_onion(self, hex_str):
        decoded_bytes = bytes.fromhex(hex_str)
        encoded_base32 = base64.b32encode(decoded_bytes).decode('utf-8').lower().rstrip('=')
        return f"{encoded_base32}.onion"






    ############################################################
    # __create_tables_if_not_exists
    ############################################################
    #
    # Creates the three _LNResearch_* staging tables. No
    # explicit commit — CREATE TABLE is DDL and auto-commits
    # in MySQL/MariaDB. The _LNResearch_ChannelUpdates table
    # stays commented out together with its parsing branch in
    # __parse_message.
    #
    # Used by:
    #   - __init__ (above)
    ############################################################

    def __create_tables_if_not_exists(self):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS `_LNResearch_ChannelAnnouncements` (
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
                    CREATE TABLE IF NOT EXISTS `_LNResearch_NodeAnnouncements` ( 
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
                    CREATE TABLE IF NOT EXISTS `_LNResearch_NodeAddresses` ( 
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

                # Dormant: staging table for channel updates —
                # pairs with the disabled type-258 branch in
                # __parse_message
                # cursor.execute(f'''
                #     CREATE TABLE IF NOT EXISTS `_LNResearch_ChannelUpdates` (
                #         `signature` CHAR(128) NOT NULL,
                #         `chain_hash` CHAR(64) NOT NULL,
                #         `short_channel_id` BIGINT NOT NULL,
                #         `timestamp` INT NOT NULL,
                #         `message_flags` TINYINT UNSIGNED NOT NULL,
                #         `channel_flags` TINYINT UNSIGNED NOT NULL,
                #         `cltv_expiry_delta` SMALLINT UNSIGNED NOT NULL,
                #         `htlc_minimum_msat` BIGINT UNSIGNED NOT NULL,
                #         `fee_base_msat` INT UNSIGNED NOT NULL,
                #         `fee_proportional_millionths` INT UNSIGNED NOT NULL,
                #         UNIQUE KEY (`short_channel_id`, `timestamp`, `channel_flags`),
                #         INDEX idx_timestamp (`timestamp`),
                #         INDEX idx_channel_flags_short_channel_id (`channel_flags`, `short_channel_id`)
                #     );
                # ''')






    ############################################################
    # insert_or_ignore_into_main
    ############################################################
    #
    # Promotes the staged channel announcements into the
    # shared Lightning_Channels table. INSERT IGNORE — rows
    # already promoted (e.g. by the LND DBReader import) stay
    # untouched. Public, but nothing outside this class calls
    # it at the moment.
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
                    FROM _LNResearch_ChannelAnnouncements ca
                ''')
                conn.commit()






    ############################################################
    # __import_data
    ############################################################
    #
    # Replays the gossip capture into the staging tables.
    # File format (lnresearch gossip dumps): a bz2 stream
    # opening with a 4-byte header — ASCII 'GSP' plus a
    # version byte that must be 1 — followed by
    # varint-length-prefixed raw gossip messages back to back.
    #
    # Used by:
    #   - __init__ (above)
    ############################################################

    def __import_data(self, filename: str):
        # STEP 1: one connection and cursor for the whole
        # replay — commits are batched below, not per row
        # ===============================================
        with get_db_connection() as db_conn:
            with db_conn.cursor() as db_cursor:

                with bz2.open(filename, 'rb') as f:


                    # STEP 2: check the magic — 'GSP' version 1
                    # (note: assert vanishes under python -O)
                    # =========================================
                    header = f.read(4)
                    assert(header[:3] == b'GSP' and header[3] == 1)


                    # STEP 3: replay the length-prefixed messages
                    # ===========================================
                    insertedMessageCounter = 0
                    while True:
                        length = varint_decode(f)
                        # QUIRK (documented, not fixed): read()
                        # runs BEFORE the None/EOF check below.
                        # At EOF varint_decode returns None and
                        # f.read(None) means "read everything
                        # left" — b'' — so this only works
                        # because read(None) happens to be legal.
                        msg = f.read(length)

                        if(length == None):
                            break

                        # A short read is a truncated trailing
                        # message — skip it, don't parse garbage
                        if len(msg) != length:
                            continue

                        self.__parse_message(db_cursor, msg)

                        # Commit in 10000-message batches —
                        # per-message commits would crawl
                        insertedMessageCounter += 1
                        if(insertedMessageCounter % 10000 == 0):
                            db_conn.commit()

                    # Flush the final partial batch
                    db_conn.commit()
