############################################################
#  [*] Entity clusters — Lightning_Entities + NodeAliases
#
#  Builds and maintains the two entity tables: every alias
#  a node has ever announced (Lightning_NodeAliases, with a
#  firstSeen/lastSeen window per NodeID+Alias pair) and the
#  single display name per node the rest of the app shows
#  (Lightning_Entities). Aliases flow in from the importer
#  staging tables (_LND_DBReader_NodeAnnouncements,
#  _LNResearch_NodeAnnouncements); downstream the entity
#  metrics selectors join against Lightning_Entities.
############################################################


import logging
import time
from datetime import datetime
from ..database.utils import get_db_connection
from ..database.raw_data_selector import RawDataSelector   # dead import — nothing in this file uses it


logger = logging.getLogger(__name__)









############################################################
# EntityClusters
############################################################
#
# Ensures both tables exist on construction, then offers
# three passes the importers run back to back:
#
#   import_node_aliases_to_main_table — staging → aliases
#   import_new_entities_to_main_table — pick display names
#   fix_entity_hex_names_if_possible  — swap hex fallbacks
#
# Used by:
#   - importLNDDBReader (blnstats/__init__.py)
#   - importLNResearchData (blnstats/__init__.py)
############################################################

class EntityClusters:






    ############################################################
    # __init__
    ############################################################
    #
    # Creates Lightning_Entities and Lightning_NodeAliases
    # when they are missing — safe to construct repeatedly,
    # which every import run does.
    #
    # Used by:
    #   - importLNDDBReader / importLNResearchData
    #     (blnstats/__init__.py) — one instance per run
    ############################################################

    def __init__(self):
        with get_db_connection() as db_conn:
            with db_conn.cursor() as db_cursor:

                db_cursor.execute('''
                    CREATE TABLE IF NOT EXISTS `Lightning_Entities` (
                        `NodeID` CHAR(66) NOT NULL,
                        `EntityName` VARCHAR(255) NOT NULL,
                        CONSTRAINT `PRIMARY` PRIMARY KEY (`NodeID`)
                    );
                ''')

                db_cursor.execute('''
                    CREATE TABLE IF NOT EXISTS `Lightning_NodeAliases` (
                        `ID` INT AUTO_INCREMENT PRIMARY KEY,
                        `NodeID` CHAR(66) NOT NULL,
                        `Alias` VARCHAR(32) NOT NULL,
                        `firstSeen` TIMESTAMP NULL,
                        `lastSeen` TIMESTAMP NULL,
                        
                        UNIQUE KEY `unique_nodeid_alias` (`NodeID`, `Alias`),
                        INDEX `idx_nodeid` (`NodeID`),
                        INDEX `idx_alias` (`Alias`)
                    );
                ''')






    ############################################################
    # import_node_aliases_to_main_table
    ############################################################
    #
    # Folds one importer staging table into
    # Lightning_NodeAliases: collapses duplicate rows into a
    # firstSeen/lastSeen window per (NodeID, Alias) pair,
    # then upserts — ON DUPLICATE KEY only ever WIDENS an
    # existing window (LEAST/GREATEST). Table and column
    # names are f-string-interpolated into the SELECT, so
    # only trusted identifiers may be passed (both callers
    # hardcode them).
    #
    # Used by:
    #   - importLNDDBReader (blnstats/__init__.py) — from
    #     _LND_DBReader_NodeAnnouncements
    #   - importLNResearchData (blnstats/__init__.py) — from
    #     _LNResearch_NodeAnnouncements
    ############################################################

    def import_node_aliases_to_main_table(self, from_table_name, from_alias_column, from_node_id_column, from_timestamp_column):
        with get_db_connection() as db_conn:
            with db_conn.cursor() as db_cursor:


                # STEP 1: fetch every row from the staging table
                # ==============================================
                logger.info(f'Fetching data from {from_table_name}')
                fetch_query = f'''
                    SELECT {from_node_id_column}, {from_alias_column}, {from_timestamp_column} FROM {from_table_name}
                '''
                db_cursor.execute(fetch_query)
                rows = db_cursor.fetchall()


                # STEP 2: collapse rows into one first/last-seen window
                # per (NodeID, Alias) pair
                # =====================================================
                logger.info(f'Preprocessing data')
                processed_data = {}
                for row in rows:
                    node_id, alias, timestamp = row

                    # nameless nodes still need something to show — fall back to the NodeID prefix
                    if(alias == ""):
                        alias = node_id[0:20]


                    # announcements dated before Lightning existed are corrupt clock data — drop
                    # them (note: fromisoformat(...).timestamp() depends on the server timezone)
                    if(timestamp < datetime.fromisoformat('2017-12-01').timestamp()):
                        continue
                    # same for timestamps from the future
                    elif(timestamp > time.time()):
                        continue


                    timestamp_dt = datetime.fromtimestamp(timestamp)

                    key = (node_id, alias)

                    if key in processed_data:
                        # repeated sighting — widen the seen-window
                        first_seen, last_seen = processed_data[key]
                        processed_data[key] = (
                            min(first_seen, timestamp_dt),
                            max(last_seen, timestamp_dt)
                        )
                    else:
                        processed_data[key] = (timestamp_dt, timestamp_dt)


                # STEP 3: upsert — an existing window only ever widens
                # ====================================================
                processed_data_list = [
                    (node_id, alias, first_seen, last_seen)
                    for (node_id, alias), (first_seen, last_seen) in processed_data.items()
                ]

                logger.info(f'Inserting processed data into the main table')
                insert_query = '''
                    INSERT INTO Lightning_NodeAliases (NodeID, Alias, firstSeen, lastSeen)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        firstSeen = LEAST(firstSeen, VALUES(firstSeen)),
                        lastSeen = GREATEST(lastSeen, VALUES(lastSeen))
                '''
                db_cursor.executemany(insert_query, processed_data_list)
                db_conn.commit()






    ############################################################
    # import_new_entities_to_main_table
    ############################################################
    #
    # Gives every known node a row in Lightning_Entities.
    # INSERT IGNORE throughout: a node that already has an
    # entity name is never renamed here. New nodes get their
    # latest alias; on a lastSeen tie the subquery matches
    # several aliases and whichever the INSERT reaches first
    # sticks. Nodes known only as channel endpoints get a
    # 20-char hex prefix of their NodeID as a placeholder
    # (cleaned up by fix_entity_hex_names_if_possible).
    #
    # Used by:
    #   - importLNDDBReader (blnstats/__init__.py)
    #   - importLNResearchData (blnstats/__init__.py)
    ############################################################

    def import_new_entities_to_main_table(self):
        with get_db_connection() as db_conn:
            with db_conn.cursor() as db_cursor:


                # STEP 1: name new nodes after their latest alias
                # ===============================================
                logger.info('Inserting new entities into Lightning_Entities')
                db_cursor.execute('''
                    INSERT IGNORE INTO Lightning_Entities (NodeID, EntityName)
                    SELECT NodeID, Alias
                    FROM Lightning_NodeAliases
                    WHERE (NodeID, lastSeen) IN (
                        SELECT NodeID, MAX(lastSeen)
                        FROM Lightning_NodeAliases
                        GROUP BY NodeID
                    )
                ''')
                db_conn.commit()


                # STEP 2: placeholder names for channel-only nodes
                # ================================================
                db_cursor.execute('''
                    INSERT IGNORE INTO Lightning_Entities (NodeID, EntityName)
                    SELECT NodeID1, SUBSTRING(NodeID1, 1, 20)
                    FROM Lightning_Channels
                ''')
                db_cursor.execute('''
                    INSERT IGNORE INTO Lightning_Entities (NodeID, EntityName)
                    SELECT NodeID2, SUBSTRING(NodeID2, 1, 20)
                    FROM Lightning_Channels
                ''')
                db_conn.commit()






    ############################################################
    # fix_entity_hex_names_if_possible
    ############################################################
    #
    # Replaces placeholder EntityNames with the node's most
    # recent non-hex alias, when one exists. A placeholder
    # is ONLY an empty name or the exact 20-char NodeID
    # prefix import_new_entities_to_main_table plants — a
    # genuine alias that merely spells a hex word ("cafe",
    # "decade") is a real name and survives. Runs one
    # SELECT per placeholder entity (N+1) — acceptable at
    # current table sizes.
    #
    # Used by:
    #   - importLNDDBReader (blnstats/__init__.py)
    #   - importLNResearchData (blnstats/__init__.py)
    ############################################################

    def fix_entity_hex_names_if_possible(self):
        with get_db_connection() as db_conn:
            with db_conn.cursor() as db_cursor:


                # STEP 1: collect entities still wearing
                # placeholder names — empty, or exactly the
                # 20-char prefix of their own NodeID
                # ===========================================
                logger.info('Fetching entities with hex string names')
                fetch_query = '''
                    SELECT NodeID, EntityName
                    FROM Lightning_Entities
                    WHERE
                        EntityName = ""
                        OR (CHAR_LENGTH(EntityName) = 20 AND NodeID LIKE CONCAT(EntityName, '%'))
                '''
                db_cursor.execute(fetch_query)
                hex_entities = db_cursor.fetchall()


                # STEP 2: swap in the freshest usable alias, if any
                # =================================================
                for node_id, entity_name in hex_entities:
                    alias_query = '''
                        SELECT Alias
                        FROM Lightning_NodeAliases
                        WHERE NodeID = %s AND Alias != %s AND Alias NOT REGEXP '^[0-9a-fA-F]+$' AND Alias != ""
                        ORDER BY lastSeen DESC
                        LIMIT 1
                    '''
                    db_cursor.execute(alias_query, (node_id, entity_name))
                    alias_result = db_cursor.fetchone()

                    if alias_result:
                        new_alias = alias_result[0]
                        logger.info(f'Updating EntityName for NodeID: {node_id} from {entity_name} to {new_alias}')
                        update_query = '''
                            UPDATE Lightning_Entities
                            SET EntityName = %s
                            WHERE NodeID = %s
                        '''
                        db_cursor.execute(update_query, (new_alias, node_id))

                db_conn.commit()
