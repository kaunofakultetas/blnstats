############################################################
#  [*] Database bootstrap — connection factory + schema DDL
#
#  The single MySQL entry point of the backend: every
#  module that touches the database imports
#  get_db_connection() from here — the selectors in
#  database/, the importers in data_import/, the cache
#  builders in data_transform/, calculations/ and the
#  api/ routes. create_app() (blnstats/__init__.py) calls
#  the two create_* functions once at startup so the
#  lnstats schema exists before anything queries it.
############################################################


import mysql.connector
from mysql.connector.cursor import MySQLCursorDict
import os

# Compose-network defaults; DB_* env vars override them
# at runtime. lnstats/lnstats doubles as the fallback
# credentials — acceptable only inside the stack's
# isolated docker network.
DEFAULT_DB_HOST = 'blnstats-mysql'
DEFAULT_DB_NAME = 'lnstats'
DEFAULT_DB_USER = 'lnstats'
DEFAULT_DB_PASSWORD = 'lnstats'








############################################################
# get_db_connection
############################################################
#
# Opens one MySQL connection from the DB_* env vars,
# with the constants above as fallback.
#
# Used by:
#   - practically every DB-touching module: the
#     selectors in database/, data_import/*,
#     data_transform/*, calculations/general_stats.py
#     and the api/auth + api/settings routes
############################################################

def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', DEFAULT_DB_HOST),
        database=os.getenv('DB_NAME', DEFAULT_DB_NAME),
        user=os.getenv('DB_USER', DEFAULT_DB_USER),
        password=os.getenv('DB_PASSWORD', DEFAULT_DB_PASSWORD)
    )
    # BUG (documented, not fixed): MySQLConnection has no
    # 'cursor_class' attribute, so this assignment is a
    # no-op — cursors stay tuple-based unless a caller
    # passes dictionary=True to conn.cursor().
    # create_tables_if_not_exists below RELIES on tuple
    # rows (fetchone()[0]).
    conn.cursor_class = MySQLCursorDict
    return conn








############################################################
# create_database_if_not_exists
############################################################
#
# Connects at server level (no schema selected — the
# point is to create it) and issues CREATE DATABASE IF
# NOT EXISTS. db_name is f-string-interpolated into the
# SQL unescaped: acceptable only because the sole
# caller passes the literal 'lnstats'. Failures are
# printed and swallowed so startup continues even if
# MySQL is not up yet.
#
# Used by:
#   - create_app() (blnstats/__init__.py) — at startup
############################################################

def create_database_if_not_exists(db_name):
    try:
        # Server-level connection on purpose — the target
        # schema may not exist yet
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', DEFAULT_DB_HOST),
            user=os.getenv('DB_USER', DEFAULT_DB_USER),
            password=os.getenv('DB_PASSWORD', DEFAULT_DB_PASSWORD)
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            cursor.execute(f" CREATE DATABASE IF NOT EXISTS {db_name} ")
            
            print(f"Database `{db_name}` created or already exists.")
            
            cursor.close()
            connection.close()

    except Exception as e:
        print(f"Error: '{e}'")








############################################################
# create_tables_if_not_exists
############################################################
#
# Bootstraps the lnstats schema: the raw blockchain /
# LN graph tables the importers fill, plus the System_*
# tables behind the auth and settings APIs. Seeds a
# default administrator and the default settings on
# first run. In MySQL every CREATE TABLE auto-commits;
# the single commit at the end covers the seed INSERTs.
# NOTE: Lightning_Entities / Lightning_NodeAliases are
# ALSO created by EntityClusters.__init__
# (data_transform/entity_clusters.py) with a diverging
# type (EntityName CHAR(255) here vs VARCHAR(255)
# there) — whichever module runs first fixes the real
# schema.
#
# Used by:
#   - create_app() (blnstats/__init__.py) — at startup
############################################################

def create_tables_if_not_exists():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:


            # STEP 1: raw blockchain + LN graph tables — the
            # importers in data_import/ fill these, the
            # selectors in database/ read them
            # ==============================================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS `Blockchain_Blocks` ( 
                    `BlockHeight` INT UNSIGNED NOT NULL,
                    `BlockHash` CHAR(64) NOT NULL,
                    `Timestamp` INT UNSIGNED NOT NULL,
                    `Time` DATETIME NOT NULL,
                    `Date` DATE NOT NULL,
                    PRIMARY KEY (`BlockHeight`),
                    CONSTRAINT `BlockHeight` UNIQUE (`BlockHeight`),
                    INDEX `idx_BlockHash` (`BlockHash`),
                    INDEX `idx_Date` (`Date`),
                    INDEX `idx_Timestamp` (`Timestamp`)
                );
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS `Blockchain_Transactions` ( 
                    `ShortChannelID` BIGINT UNSIGNED NOT NULL,
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
                    INDEX `idx_funding_spending_value_covering` (`FundingBlockIndex`, `SpendingBlockIndex`, `Value`),
                    INDEX `idx_Value` (`Value`)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS `Lightning_Channels` (
                    `ShortChannelID` BIGINT NOT NULL,
                    `BlockIndex` INT NOT NULL,
                    `TxIndex` INT NOT NULL,
                    `OutputIndex` INT NOT NULL,
                    `NodeID1` CHAR(66) NOT NULL,
                    `NodeID2` CHAR(66) NOT NULL,
                    PRIMARY KEY (`ShortChannelID`),
                    INDEX idx_node_id_1 (`NodeID1`),
                    INDEX idx_node_id_2 (`NodeID2`),
                    INDEX idx_blockindex_txindex (`BlockIndex`, `TxIndex`)
                );
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS `Lightning_Entities` ( 
                    `NodeID` CHAR(66) NOT NULL,
                    `EntityName` CHAR(255) NOT NULL,
                    PRIMARY KEY (`NodeID`)
                );
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS `Lightning_NodeAliases` ( 
                    `ID` INT AUTO_INCREMENT NOT NULL,
                    `NodeID` CHAR(66) NOT NULL,
                    `Alias` VARCHAR(32) NOT NULL,
                    `firstSeen` TIMESTAMP NULL,
                    `lastSeen` TIMESTAMP NULL,
                    PRIMARY KEY (`ID`),
                    CONSTRAINT `unique_nodeid_alias` UNIQUE (`NodeID`, `Alias`),
                    INDEX `idx_alias` (`Alias`),
                    INDEX `idx_nodeid` (`NodeID`)
                );
            ''')


            # STEP 2: System_Users — seed the default
            # admin@admin.com account (bcrypt hash) only when
            # the table is brand new / empty
            # ===============================================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS `System_Users` (
                    `ID` INT NOT NULL AUTO_INCREMENT,
                    `Email` VARCHAR(255) NOT NULL UNIQUE,
                    `Password` VARCHAR(255) NOT NULL,
                    `Admin` TINYINT(1) NOT NULL DEFAULT 0,
                    `Enabled` TINYINT(1) NOT NULL DEFAULT 1,
                    `LastSeen` TIMESTAMP NULL DEFAULT NULL,
                    `CreatedAt` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    `UpdatedAt` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (`ID`)
                );
            ''')
            # STEP 2.1: fetchone()[0] works because cursors are
            # tuple-based (see the get_db_connection banner)
            cursor.execute('SELECT COUNT(*) FROM System_Users')
            result = cursor.fetchone()[0]
            if result == 0:
                cursor.execute('INSERT INTO System_Users (Email, Password, Admin, Enabled) VALUES (%s,%s,%s,%s)',
                               ('admin@admin.com', '$2a$12$/ZIb.Mw5ZEPlPdqNkC3A3.O9hySEuhrt2FpaU9y1iMWVVW4RYTIW2', 1, 1))


            # STEP 3: System_Settings — seed the initial-sync
            # flag and the default LND-DBReader source URL; the
            # commit below also covers the STEP 2 INSERT
            # =================================================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS `System_Settings` (
                    `Key` VARCHAR(255) NOT NULL UNIQUE,
                    `Value` VARCHAR(255) DEFAULT NULL,
                    PRIMARY KEY (`Key`)
                );
            ''')
            # INSERT IGNORE keeps values already edited via the
            # settings API — these are first-boot defaults only
            cursor.execute('INSERT IGNORE INTO System_Settings (`Key`, `Value`) VALUES (%s,%s)',
                            ('InitialSyncCompleted', '0'))
            cursor.execute('INSERT IGNORE INTO System_Settings (`Key`, `Value`) VALUES (%s,%s)',
                            ('LND-DBReader-Source-1', 'https://blnstats.knf.vu.lt/rawdata/INPUT/lnd-dbreader-A336EEAB--latest.json.gz'))
            conn.commit()








############################################################
# get_setting
############################################################
#
# One System_Settings value by key, with a caller-supplied
# default when the key is absent. Values are stored and
# returned as strings; a DB error raises like everywhere
# else — only a MISSING key falls back to the default.
#
# Used by:
#   - workflows.py — lnd_dbreader_full_update_flow and
#     full_initialization_flow resolve the DBReader dump
#     URL ('LND-DBReader-Source-1') through this
#   - tests/test_database_selectors.py
############################################################

def get_setting(key, default=None):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT `Value` FROM System_Settings WHERE `Key` = %s', [key])
            row = cursor.fetchone()
            return row[0] if row else default


