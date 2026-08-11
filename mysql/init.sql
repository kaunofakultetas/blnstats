############################################################
#  [*] lnstats schema bootstrap — one authoritative DDL
#
#  Runs once via the mysql image entrypoint on a FRESH data
#  directory (mount as
#  ./mysql/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
#  in docker-compose.yml; an existing _DATA/mysql/data skips
#  it entirely). The backend's scattered CREATE TABLE IF NOT
#  EXISTS calls then no-op against these tables, which makes
#  this file the single source of truth the code copies had
#  been drifting from.
#
#  Divergences resolved here (code copies disagree):
#    - Blockchain_Transactions: keeps the covering index
#      that database/utils.py has and the importer copy
#      lacks
#    - Lightning_Entities.EntityName: VARCHAR(255) (the
#      entity_clusters.py version) — utils.py's CHAR(255)
#      would space-pad every name
#    - ShortChannelID: BIGINT UNSIGNED in BOTH channel
#      tables (they disagreed signed/unsigned, which also
#      blocked the foreign key)
#    - _CACHED1_NodeMetrics.BlockHeight: INT UNSIGNED to
#      match Blockchain_Blocks
#
#  Relationships: real FOREIGN KEYs exist only where the
#  import order provably guarantees them. NodeID columns
#  are deliberately NOT keyed — gossip is eventually
#  consistent (aliases and entities arrive before/after
#  their channels in either order), and the _LNResearch_* /
#  _LND_DBReader_* staging tables are raw dump mirrors that
#  must accept anything the source ships.
############################################################


CREATE DATABASE IF NOT EXISTS lnstats CHARACTER SET utf8mb4;
USE lnstats;




############################################################
# Blockchain_Blocks
############################################################
#
# One row per Bitcoin block height: hash, raw UNIX
# timestamp and its rendered Time/Date. Filled by
# data_import/blockchain_blocks.py; read by
# database/raw_data_selector.py (first block per month) and
# the channel-lifetime queries.
############################################################

CREATE TABLE IF NOT EXISTS `Blockchain_Blocks` (
    `BlockHeight` INT UNSIGNED NOT NULL,
    `BlockHash` CHAR(64) NOT NULL,
    `Timestamp` INT UNSIGNED NOT NULL,
    `Time` DATETIME NOT NULL,
    `Date` DATE NOT NULL,
    PRIMARY KEY (`BlockHeight`),
    INDEX `idx_BlockHash` (`BlockHash`),
    INDEX `idx_Date` (`Date`),
    INDEX `idx_Timestamp` (`Timestamp`)
);




############################################################
# Lightning_Channels
############################################################
#
# The merged channel graph — the union both gossip
# importers (ln_research.py, lnd_dbreader.py) promote their
# staging rows into via INSERT IGNORE. ShortChannelID
# encodes (BlockIndex, TxIndex, OutputIndex).
############################################################

CREATE TABLE IF NOT EXISTS `Lightning_Channels` (
    `ShortChannelID` BIGINT UNSIGNED NOT NULL,
    `BlockIndex` INT NOT NULL,
    `TxIndex` INT NOT NULL,
    `OutputIndex` INT NOT NULL,
    `NodeID1` CHAR(66) NOT NULL,
    `NodeID2` CHAR(66) NOT NULL,
    PRIMARY KEY (`ShortChannelID`),
    INDEX `idx_node_id_1` (`NodeID1`),
    INDEX `idx_node_id_2` (`NodeID2`),
    INDEX `idx_blockindex_txindex` (`BlockIndex`, `TxIndex`)
);




############################################################
# Blockchain_Transactions
############################################################
#
# On-chain anchor per channel: funding output details and
# the spending (closing) transaction when one exists.
# SpendingBlockIndex conventions: 999999999 = verified and
# still open; 0 = tombstone, the claimed funding outpoint
# does not exist on-chain (bogus gossip — empty txids, zero
# value, permanently skipped by the sync and invisible to
# every metric). Filled by
# data_import/blockchain_transactions.py, which only ever
# processes ShortChannelIDs SELECTed from
# Lightning_Channels — hence the FK is always satisfiable;
# CASCADE so a removed channel takes its anchor row along.
############################################################

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
    INDEX `idx_Value` (`Value`),
    CONSTRAINT `fk_bt_channel`
        FOREIGN KEY (`ShortChannelID`) REFERENCES `Lightning_Channels` (`ShortChannelID`)
        ON DELETE CASCADE ON UPDATE CASCADE
);




############################################################
# Lightning_NodeAliases
############################################################
#
# Every (node, alias) pair ever announced, with its
# first/last sighting. Filled by both gossip importers; read
# by entity_clusters.py when naming entities. No FK on
# NodeID — aliases legitimately arrive for nodes that have
# no channel yet.
############################################################

CREATE TABLE IF NOT EXISTS `Lightning_NodeAliases` (
    `ID` INT AUTO_INCREMENT NOT NULL,
    `NodeID` CHAR(66) NOT NULL,
    `Alias` VARCHAR(32) NOT NULL,
    `firstSeen` TIMESTAMP NULL,
    `lastSeen` TIMESTAMP NULL,
    PRIMARY KEY (`ID`),
    CONSTRAINT `unique_nodeid_alias` UNIQUE (`NodeID`, `Alias`),
    INDEX `idx_nodeid` (`NodeID`),
    INDEX `idx_alias` (`Alias`)
);




############################################################
# Lightning_Entities
############################################################
#
# One display name per node — the entity view the entity
# metrics group by. Filled by entity_clusters.py (latest
# alias, else a 20-hex NodeID-prefix placeholder). No FK on
# NodeID for the same eventual-consistency reason as above.
############################################################

CREATE TABLE IF NOT EXISTS `Lightning_Entities` (
    `NodeID` CHAR(66) NOT NULL,
    `EntityName` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`NodeID`)
);




############################################################
# _CACHED1_NodeMetrics
############################################################
#
# Precomputed per-node capacity and channel count for the
# first block of every month — rebuilt height by height
# (DELETE + batched INSERT) by data_transform/
# node_metrics.py, read by the metrics selectors. FK to
# Blockchain_Blocks: the transform only ever runs on
# heights SELECTed from that table.
############################################################

CREATE TABLE IF NOT EXISTS `_CACHED1_NodeMetrics` (
    `BlockHeight` INT UNSIGNED NOT NULL,
    `NodeID` VARCHAR(66) NOT NULL,
    `ChannelCount` INTEGER NOT NULL,
    `Capacity` BIGINT NOT NULL,
    PRIMARY KEY (`BlockHeight`, `NodeID`),
    INDEX `idx_blockheight` (`BlockHeight`),
    INDEX `idx_nodeid` (`NodeID`),
    CONSTRAINT `fk_cache_block`
        FOREIGN KEY (`BlockHeight`) REFERENCES `Blockchain_Blocks` (`BlockHeight`)
        ON DELETE CASCADE ON UPDATE CASCADE
);




############################################################
# _LNResearch_* — raw staging for the LN Research dataset
############################################################
#
# Verbatim landing zone for the gossip capture parsed by
# data_import/ln_research.py; promoted into
# Lightning_Channels / Lightning_NodeAliases afterwards.
# Standalone by design — no FKs, the dump defines itself.
############################################################

CREATE TABLE IF NOT EXISTS `_LNResearch_ChannelAnnouncements` (
    `ShortChannelID` BIGINT NOT NULL,
    `BlockIndex` INT NOT NULL,
    `TxIndex` INT NOT NULL,
    `OutputIndex` INT NOT NULL,
    `NodeID1` CHAR(66) NOT NULL,
    `NodeID2` CHAR(66) NOT NULL,
    PRIMARY KEY (`ShortChannelID`)
);

CREATE TABLE IF NOT EXISTS `_LNResearch_NodeAnnouncements` (
    `ID` INT AUTO_INCREMENT NOT NULL,
    `NodeID` CHAR(66) NOT NULL,
    `Alias` VARCHAR(32) NOT NULL,
    `FirstSeen` INT NOT NULL,
    `LastSeen` INT NOT NULL,
    PRIMARY KEY (`ID`),
    CONSTRAINT `unique_nodeid_alias` UNIQUE (`NodeID`, `Alias`)
);

CREATE TABLE IF NOT EXISTS `_LNResearch_NodeAddresses` (
    `ID` INT AUTO_INCREMENT NOT NULL,
    `NodeID` CHAR(66) NOT NULL,
    `Address` VARCHAR(255) NOT NULL,
    `Port` INT NOT NULL,
    `FirstSeen` INT NOT NULL,
    `LastSeen` INT NOT NULL,
    PRIMARY KEY (`ID`),
    CONSTRAINT `unique_nodeid_address_port` UNIQUE (`NodeID`, `Address`, `Port`)
);

# Dormant: pairs with the disabled type-258 (channel_update)
# branch in ln_research.py __parse_message — uncomment both
# together.
# CREATE TABLE IF NOT EXISTS `_LNResearch_ChannelUpdates` (
#     `signature` CHAR(128) NOT NULL,
#     `chain_hash` CHAR(64) NOT NULL,
#     `short_channel_id` BIGINT NOT NULL,
#     `timestamp` INT NOT NULL,
#     `message_flags` TINYINT UNSIGNED NOT NULL,
#     `channel_flags` TINYINT UNSIGNED NOT NULL,
#     `cltv_expiry_delta` SMALLINT UNSIGNED NOT NULL,
#     `htlc_minimum_msat` BIGINT UNSIGNED NOT NULL,
#     `fee_base_msat` INT UNSIGNED NOT NULL,
#     `fee_proportional_millionths` INT UNSIGNED NOT NULL,
#     UNIQUE KEY (`short_channel_id`, `timestamp`, `channel_flags`),
#     INDEX `idx_timestamp` (`timestamp`),
#     INDEX `idx_channel_flags_short_channel_id` (`channel_flags`, `short_channel_id`)
# );




############################################################
# _LND_DBReader_* — raw staging for the LND DBReader dump
############################################################
#
# Same shape and role as the _LNResearch_* tables, fed by
# data_import/lnd_dbreader.py from the faculty node's JSON
# dump.
############################################################

CREATE TABLE IF NOT EXISTS `_LND_DBReader_ChannelAnnouncements` (
    `ShortChannelID` BIGINT NOT NULL,
    `BlockIndex` INT NOT NULL,
    `TxIndex` INT NOT NULL,
    `OutputIndex` INT NOT NULL,
    `NodeID1` CHAR(66) NOT NULL,
    `NodeID2` CHAR(66) NOT NULL,
    PRIMARY KEY (`ShortChannelID`)
);

CREATE TABLE IF NOT EXISTS `_LND_DBReader_NodeAnnouncements` (
    `ID` INT AUTO_INCREMENT NOT NULL,
    `NodeID` CHAR(66) NOT NULL,
    `Alias` VARCHAR(32) NOT NULL,
    `FirstSeen` INT NOT NULL,
    `LastSeen` INT NOT NULL,
    PRIMARY KEY (`ID`),
    CONSTRAINT `unique_nodeid_alias` UNIQUE (`NodeID`, `Alias`)
);

CREATE TABLE IF NOT EXISTS `_LND_DBReader_NodeAddresses` (
    `ID` INT AUTO_INCREMENT NOT NULL,
    `NodeID` CHAR(66) NOT NULL,
    `Address` VARCHAR(255) NOT NULL,
    `Port` INT NOT NULL,
    `FirstSeen` INT NOT NULL,
    `LastSeen` INT NOT NULL,
    PRIMARY KEY (`ID`),
    CONSTRAINT `unique_nodeid_address_port` UNIQUE (`NodeID`, `Address`, `Port`)
);




############################################################
# System_Users / System_Settings — the admin side
############################################################
#
# Accounts for the admin UI (api/auth) and the key/value
# settings store (api/settings). Seeds mirror the ones
# database/utils.py plants on first run: the default
# admin@admin.com account (bcrypt hash, change the password
# after first login) and the first-boot settings defaults.
############################################################

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

CREATE TABLE IF NOT EXISTS `System_Settings` (
    `Key` VARCHAR(255) NOT NULL UNIQUE,
    `Value` VARCHAR(255) DEFAULT NULL,
    PRIMARY KEY (`Key`)
);

INSERT IGNORE INTO `System_Users` (`Email`, `Password`, `Admin`, `Enabled`)
VALUES ('admin@admin.com', '$2a$12$/ZIb.Mw5ZEPlPdqNkC3A3.O9hySEuhrt2FpaU9y1iMWVVW4RYTIW2', 1, 1);

INSERT IGNORE INTO `System_Settings` (`Key`, `Value`)
VALUES ('InitialSyncCompleted', '0'),
       ('LND-DBReader-Source-1', 'https://blnstats.knf.vu.lt/rawdata/INPUT/lnd-dbreader-A336EEAB--latest.json.gz');
